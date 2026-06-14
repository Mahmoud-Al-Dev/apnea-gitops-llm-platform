import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from scipy.signal import butter, filtfilt, hilbert, resample, detrend
from scipy.ndimage import uniform_filter1d, median_filter
from sklearn.preprocessing import StandardScaler


# ============================================================
# 1. MODEL ARCHITECTURE
# ============================================================
class ConvLSTM(nn.Module):
    """
    Matches the training architecture in train_lstm.py.
    Input shape: (batch, seq_len, 6)
    Output shape: (batch, 2, seq_len)
    """
    def __init__(self, input_size=6, hidden_size=128, num_layers=2):
        super().__init__()

        self.cnn = nn.Sequential(
            nn.Conv1d(in_channels=input_size, out_channels=32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
        )

        self.lstm = nn.LSTM(
            input_size=32,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
        )

        self.fc = nn.Linear(hidden_size * 2, 2)

    def forward(self, x):
        # x: (batch, seq_len, features)
        x = x.permute(0, 2, 1)              # -> (batch, features, seq_len)
        cnn_features = self.cnn(x)
        cnn_features = cnn_features.permute(0, 2, 1)  # -> (batch, seq_len, channels)

        lstm_out, _ = self.lstm(cnn_features)
        predictions = self.fc(lstm_out)     # -> (batch, seq_len, 2)
        predictions = predictions.permute(0, 2, 1)  # -> (batch, 2, seq_len)
        return predictions


# ============================================================
# 2. GLOBALS / PATHS
# ============================================================
OSA_MODEL = None
CA_MODEL = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OSA_WEIGHTS_PATH = os.path.join(BASE_DIR, "penta_lstm_OSA_weights.pth")
CA_WEIGHTS_PATH = os.path.join(BASE_DIR, "penta_lstm_CA_weights.pth")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Inference thresholds
OSA_THRESHOLD = 0.5
CA_THRESHOLD = 0.5

# Signal processing constants
FS_ORIGINAL = 256
FS_TARGET = 32
TRIM_SEC = 0            # 20 minutes from start and end
WINDOW_SEC = 30
STEP_SEC = 20              # 10s overlap => 20s step

# Final 6 channels used for training
# [3, 11, 14, 15, 17, 18] from engineered features
CORE_FEATURE_NAMES = [
    "PFlow_Clean",
    "Thorax_Width",
    "Abdomen_Width",
    "SaO2_Smooth",
    "Effort_Flow_Ratio",
    "SaO2_Deriv",
]


# ============================================================
# 3. MODEL LOADING
# ============================================================
def _load_single_model(weights_path: str, label: str):
    model = ConvLSTM(input_size=6).to(DEVICE)

    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"{label} weights file not found: {weights_path}")

    state_dict = torch.load(weights_path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.eval()

    print(f"{label} model weights loaded successfully from {weights_path}")
    return model


def load_models():
    global OSA_MODEL, CA_MODEL

    if OSA_MODEL is None:
        OSA_MODEL = _load_single_model(OSA_WEIGHTS_PATH, "OSA")

    if CA_MODEL is None:
        CA_MODEL = _load_single_model(CA_WEIGHTS_PATH, "CA")

    return OSA_MODEL, CA_MODEL


# ============================================================
# 4. SIGNAL PROCESSING HELPERS
# ============================================================
def apply_lowpass(signal, cutoff, fs, order=2):
    nyq = 0.5 * fs
    b, a = butter(order, cutoff / nyq, btype="low")
    return filtfilt(b, a, signal)


def apply_bandpass(signal, lowcut, highcut, fs, order=2):
    nyq = 0.5 * fs
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype="bandpass")
    return filtfilt(b, a, signal)


# ============================================================
# 5. PREPROCESSING PIPELINE
# ============================================================
def preprocess_raw_signal(df: pd.DataFrame, save_features: bool = False):


    required_cols = ["PFlow", "Thorax", "Abdomen", "SaO2", "Vitalog1", "Vitalog2", "time_sec"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if len(df) < 2:
        raise ValueError("Input CSV is too short.")

    data = df.copy().reset_index(drop=True)

    # ------------------------------------------------------------
    # A. 20-minute trimming from beginning and end
    # ------------------------------------------------------------
    real_start = float(data["time_sec"].iloc[0])
    real_end = float(data["time_sec"].iloc[-1])

    window_start = real_start + TRIM_SEC
    window_end = real_end - TRIM_SEC

    if window_end <= window_start:
        raise ValueError("Recording is too short after 20-minute trimming on both ends.")

    data = data[(data["time_sec"] >= window_start) & (data["time_sec"] <= window_end)].copy()

    if len(data) < 2:
        raise ValueError("No usable data remains after trimming.")

    # ------------------------------------------------------------
    # B. Remove sensor dropouts
    # ------------------------------------------------------------
    valid_sao2_mask = data["SaO2"] > 10
    data = data[valid_sao2_mask].copy()

    if len(data) < 2:
        raise ValueError("No usable data remains after removing SaO2 dropouts.")

    # ------------------------------------------------------------
    # C. Stitch data together with rebuilt time axis
    # ------------------------------------------------------------
    data.reset_index(drop=True, inplace=True)
    new_time_axis = np.arange(len(data)) / FS_ORIGINAL + window_start
    data["time_sec"] = new_time_axis

    # ------------------------------------------------------------
    # D. Detrending / cleaning
    # ------------------------------------------------------------
    data["PFlow_Detrend"] = detrend(data["PFlow"].values)
    data["Thorax_Detrend"] = detrend(data["Thorax"].values)
    data["Abdomen_Detrend"] = detrend(data["Abdomen"].values)

    data["Vitalog1_Med"] = median_filter(data["Vitalog1"].values, size=FS_ORIGINAL)
    data["Vitalog2_Med"] = median_filter(data["Vitalog2"].values, size=FS_ORIGINAL)

    data["Vitalog1_Clean"] = apply_lowpass(data["Vitalog1_Med"].values, 2.0, FS_ORIGINAL)
    data["Vitalog2_Clean"] = apply_lowpass(data["Vitalog2_Med"].values, 2.0, FS_ORIGINAL)

    data["SaO2_Smooth"] = uniform_filter1d(data["SaO2"].values, size=512)

    data["PFlow_Clean"] = apply_bandpass(data["PFlow_Detrend"].values, 0.15, 0.7, FS_ORIGINAL)
    data["Thorax_Clean"] = apply_bandpass(data["Thorax_Detrend"].values, 0.1, 0.3, FS_ORIGINAL)
    data["Abdomen_Clean"] = apply_bandpass(data["Abdomen_Detrend"].values, 0.1, 0.3, FS_ORIGINAL)

    # ------------------------------------------------------------
    # E. Envelopes / widths
    # ------------------------------------------------------------
    data["PFlow_Upper"] = np.abs(hilbert(data["PFlow_Clean"].values))
    data["PFlow_Lower"] = -data["PFlow_Upper"]
    data["PFlow_Width"] = data["PFlow_Upper"] - data["PFlow_Lower"]

    data["Thorax_Upper"] = np.abs(hilbert(data["Thorax_Clean"].values))
    data["Thorax_Lower"] = -data["Thorax_Upper"]
    data["Thorax_Width"] = data["Thorax_Upper"] - data["Thorax_Lower"]

    data["Abdomen_Upper"] = np.abs(hilbert(data["Abdomen_Clean"].values))
    data["Abdomen_Lower"] = -data["Abdomen_Upper"]
    data["Abdomen_Width"] = data["Abdomen_Upper"] - data["Abdomen_Lower"]

    # ------------------------------------------------------------
    # F. Engineered features
    # ------------------------------------------------------------
    rolling_window = 5 * FS_ORIGINAL
    data["Thorax_Abdomen_Corr"] = (
        data["Thorax_Width"]
        .rolling(window=rolling_window, center=True)
        .corr(data["Abdomen_Width"])
    )
    data["Thorax_Abdomen_Corr"] = data["Thorax_Abdomen_Corr"].bfill().ffill()

    data["Effort_Flow_Ratio"] = (
        (data["Thorax_Width"] + data["Abdomen_Width"]) / (data["PFlow_Width"] + 0.001)
    )

    data["SaO2_Deriv"] = np.gradient(data["SaO2_Smooth"].values)

    phase_thorax = np.unwrap(np.angle(hilbert(data["Thorax_Clean"].values)))
    phase_abdomen = np.unwrap(np.angle(hilbert(data["Abdomen_Clean"].values)))
    data["Phase_Angle"] = np.abs(phase_thorax - phase_abdomen)

    data["PFlow_Var"] = data["PFlow_Clean"].rolling(window=3 * FS_ORIGINAL, center=True).var()
    data["PFlow_Var"] = data["PFlow_Var"].bfill().ffill()

    # Full feature stack, matching your development pipeline
    feature_columns = [
        "PFlow", "Thorax", "Abdomen",                       # 0, 1, 2
        "PFlow_Clean", "Thorax_Clean", "Abdomen_Clean",    # 3, 4, 5
        "PFlow_Upper", "PFlow_Lower", "PFlow_Width",       # 6, 7, 8
        "Thorax_Upper", "Thorax_Lower", "Thorax_Width",    # 9, 10, 11
        "Abdomen_Upper", "Abdomen_Lower", "Abdomen_Width", # 12, 13, 14
        "SaO2_Smooth", "Thorax_Abdomen_Corr", "Effort_Flow_Ratio",  # 15, 16, 17
        "SaO2_Deriv", "Phase_Angle", "PFlow_Var",          # 18, 19, 20
        "Vitalog1_Clean", "Vitalog2_Clean"                 # 21, 22
    ]

    features_256hz = data[feature_columns].values
    time_256hz = data["time_sec"].values

    # ------------------------------------------------------------
    # G. Downsample 256 Hz -> 32 Hz
    # ------------------------------------------------------------
    downsample_ratio = FS_TARGET / FS_ORIGINAL
    target_length = int(len(features_256hz) * downsample_ratio)

    if target_length < FS_TARGET * WINDOW_SEC:
        raise ValueError("Not enough data after preprocessing to create one inference segment.")

    features_32hz = resample(features_256hz, target_length)
    time_32hz = np.linspace(time_256hz[0], time_256hz[-1], target_length)

    # ------------------------------------------------------------
    # H. Segment into 30s windows with 10s overlap
    # ------------------------------------------------------------
    win_samples = WINDOW_SEC * FS_TARGET
    step_samples = STEP_SEC * FS_TARGET

    segments = []
    segment_times = []

    for i in range(0, len(features_32hz) - win_samples + 1, step_samples):
        segments.append(features_32hz[i:i + win_samples, :])
        segment_times.append(time_32hz[i:i + win_samples])

    if len(segments) == 0:
        raise ValueError("No segments created from preprocessed signal.")

    segments = np.array(segments)
    segment_times = np.array(segment_times)

    # ------------------------------------------------------------
    # I. Segment-wise normalization
    # ------------------------------------------------------------
    normalized_segments = np.zeros_like(segments)
    VAR_IDX = 20  # PFlow_Var in full feature stack

    for i in range(segments.shape[0]):
        seg = segments[i]
        scaler = StandardScaler()
        norm_seg = scaler.fit_transform(seg)

        stds = np.std(seg, axis=0)

        for col in range(seg.shape[1]):
            if col == VAR_IDX:
                if stds[col] == 0:
                    norm_seg[:, col] = 0.0
                continue

            if stds[col] < 1e-4:
                norm_seg[:, col] = 0.0

        normalized_segments[i] = norm_seg

    # ------------------------------------------------------------
    # J. Extract the actual 6 channels used for training
    # ------------------------------------------------------------
    core_indices = [3, 11, 14, 15, 17, 18]
    X_input = normalized_segments[:, :, core_indices]

    # Optional save for debugging / development
    if save_features:
        np.save(os.path.join(BASE_DIR, "X_inference.npy"), X_input)
        np.save(os.path.join(BASE_DIR, "segment_times.npy"), segment_times)

        selected_32hz = pd.DataFrame(
            features_32hz[:, core_indices],
            columns=CORE_FEATURE_NAMES
        )
        selected_32hz["time_sec"] = time_32hz
        selected_32hz.to_csv(
            os.path.join(BASE_DIR, "processed_features_32hz.csv"),
            index=False
        )

    processed_df_32hz = pd.DataFrame(
        features_32hz[:, core_indices],
        columns=CORE_FEATURE_NAMES
    )
    processed_df_32hz["time_sec"] = time_32hz

    return X_input, segment_times, processed_df_32hz


# ============================================================
# 6. INFERENCE HELPERS
# ============================================================
def _window_apnea_probability(model: nn.Module, input_tensor: torch.Tensor) -> np.ndarray:
    """
    Returns one apnea probability per segment by averaging the
    positive-class probability over the full sequence.
    """
    with torch.no_grad():
        logits = model(input_tensor)           # (batch, 2, seq_len)
        probs = torch.softmax(logits, dim=1)
        apnea_probs = probs[:, 1, :]           # positive class over time
        window_probs = apnea_probs.mean(dim=1)

    return window_probs.cpu().numpy()


# ============================================================
# 7. MAIN PREDICTION PIPELINE
# ============================================================
def process_csv_and_predict(df: pd.DataFrame, save_features: bool = False):
    osa_model, ca_model = load_models()

    X_input, segment_times, _ = preprocess_raw_signal(df, save_features=save_features)

    input_tensor = torch.from_numpy(X_input).float().to(DEVICE)

    osa_window_probs = _window_apnea_probability(osa_model, input_tensor)
    ca_window_probs = _window_apnea_probability(ca_model, input_tensor)

    results = []
    num_windows = X_input.shape[0]

    for i in range(num_windows):
        actual_start_time = float(segment_times[i][0])
        actual_end_time = float(segment_times[i][-1])

        osa_prob = float(osa_window_probs[i])
        ca_prob = float(ca_window_probs[i])

        osa_positive = osa_prob >= OSA_THRESHOLD
        ca_positive = ca_prob >= CA_THRESHOLD

        if osa_positive and ca_positive:
            predicted_class = "OSA" if osa_prob >= ca_prob else "Central Apnea"
            confidence = max(osa_prob, ca_prob)
            is_apnea = True
        elif osa_positive:
            predicted_class = "OSA"
            confidence = osa_prob
            is_apnea = True
        elif ca_positive:
            predicted_class = "Central Apnea"
            confidence = ca_prob
            is_apnea = True
        else:
            predicted_class = "Normal"
            confidence = max(1.0 - osa_prob, 1.0 - ca_prob)
            is_apnea = False

        results.append({
            "window_index": i,
            "start_time_sec": actual_start_time,
            "end_time_sec": actual_end_time,
            "predicted_class": predicted_class,
            "confidence": round(float(confidence), 4),
            "osa_confidence": round(osa_prob, 4),
            "ca_confidence": round(ca_prob, 4),
            "is_apnea": is_apnea,
        })

    return results