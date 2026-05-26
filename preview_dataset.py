import os
import random

import cv2
import numpy as np
import pandas as pd

from gesture_config import LABEL_TO_COMMAND

BASE_DIR = os.path.dirname(__file__)
CSV_FILE = os.path.join(BASE_DIR, "dataset_cuchi.csv")
OUT_DIR = os.path.join(BASE_DIR, "dataset_landmark_preview")

SAMPLES_PER_LABEL = 30
CANVAS_SIZE = 512
POINT_RADIUS = 4
LINE_THICKNESS = 2

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17), (5, 17),
]


def render_landmarks(points_xy: np.ndarray) -> np.ndarray:
    """Render 21x2 points (relative coords) into a preview image."""
    img = np.full((CANVAS_SIZE, CANVAS_SIZE, 3), 255, dtype=np.uint8)

    max_abs = float(np.max(np.abs(points_xy))) if points_xy.size else 1.0
    if max_abs < 1e-6:
        max_abs = 1.0

    scale = (CANVAS_SIZE * 0.40) / max_abs
    cx = CANVAS_SIZE // 2
    cy = CANVAS_SIZE // 2

    pts = np.zeros((21, 2), dtype=np.int32)
    pts[:, 0] = (cx + points_xy[:, 0] * scale).astype(np.int32)
    pts[:, 1] = (cy + points_xy[:, 1] * scale).astype(np.int32)

    for a, b in HAND_CONNECTIONS:
        cv2.line(img, tuple(pts[a]), tuple(pts[b]), (0, 200, 0), LINE_THICKNESS)

    for x, y in pts:
        cv2.circle(img, (int(x), int(y)), POINT_RADIUS, (0, 0, 255), -1)

    return img


def main() -> None:
    if not os.path.isfile(CSV_FILE):
        print(f"Không tìm thấy CSV: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)
    if df.empty:
        print("CSV đang rỗng.")
        return

    if "label" not in df.columns:
        print("CSV thiếu cột 'label'.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)

    df["label"] = df["label"].astype(int)
    labels = sorted(df["label"].unique().tolist())

    print(f"Đang xuất preview landmark -> {os.path.abspath(OUT_DIR)}")

    for label in labels:
        cmd = LABEL_TO_COMMAND.get(int(label), str(label))
        subdir = os.path.join(OUT_DIR, f"{int(label):02d}_{cmd}")
        os.makedirs(subdir, exist_ok=True)

        rows = df[df["label"] == label]
        if rows.empty:
            continue

        n = min(SAMPLES_PER_LABEL, len(rows))
        # random sample but stable-ish
        sample_indices = rows.sample(n=n, random_state=42).index.tolist()

        for i, idx in enumerate(sample_indices, start=1):
            row = df.loc[idx]
            coords = row.iloc[1:].to_numpy(dtype=np.float32)
            if coords.size != 42:
                continue
            pts = coords.reshape(21, 2)

            img = render_landmarks(pts)
            out_path = os.path.join(subdir, f"sample_{i:03d}.png")
            cv2.imwrite(out_path, img)

    print("Xong.")


if __name__ == "__main__":
    main()
