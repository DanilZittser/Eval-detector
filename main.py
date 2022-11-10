from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Union

import click
import numpy as np
import pandas as pd
from nptyping import NDArray, Shape, Int32, Float32


AbsoluteNDArrayBoxes = NDArray[Shape['*, [left, top, right, bottom]'], Int32]
RelativeNDArrayBoxes = NDArray[Shape['*, [left, top, right, bottom]'], Float32]
NDArrayBoxes = Union[AbsoluteNDArrayBoxes, RelativeNDArrayBoxes]


def compute_iou(boxes1: NDArrayBoxes, boxes2: NDArrayBoxes) -> NDArray[Shape['* num_boxes1, * num_boxes2'], Float32]:
    """Computes pairwise IOU matrix.
    Args:
        boxes1: matrix with shape `(M, 4)` where each row is of the format `[left, top, right, bottom]`
        boxes2: matrix with shape `(N, 4)` where each row is of the format `[left, top, right, bottom]`
    Returns:
        matrix with shape `(M, N)`
    """
    lu = np.maximum(boxes1[:, None, :2], boxes2[:, :2])
    rd = np.minimum(boxes1[:, None, 2:], boxes2[:, 2:])
    intersection = np.maximum(0.0, rd - lu)
    intersection_area = intersection[:, :, 0] * intersection[:, :, 1]
    boxes1_area = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])
    boxes2_area = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])
    union_area = np.maximum(boxes1_area[:, None] + boxes2_area - intersection_area, 1e-32)
    return np.clip(intersection_area / union_area, 0.0, 1.0).astype(np.float32)


def read_detections_file(filepath: Path, is_ground_truth: bool) -> pd.DataFrame:
    columns: List[str] = ['image_name', 'box', 'label'] + (['score'] if not is_ground_truth else [])
    data: pd.DataFrame = pd.read_csv(filepath, sep=' ', header=None, names=columns)

    if is_ground_truth:
        data['score'] = 1.0

    data: pd.DataFrame = pd.merge(
        left=data,
        right=pd.DataFrame(data['box'].str.split(',').tolist(), columns=['left', 'top', 'right', 'bottom']).astype(int),
        left_index=True,
        right_index=True,
    )

    return data[['image_name', 'left', 'top', 'right', 'bottom', 'label', 'score']]


@click.command()
@click.option('-g', type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path), help='Path to ground truth file')
@click.option('-d', type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path), help='Path to detection results file')
@click.option('-t', type=float, help='Overlap threshold')
def main(g: Path, d: Path, t: float):
    ground_truth: pd.DataFrame = read_detections_file(g, is_ground_truth=True)
    detection_results: pd.DataFrame = read_detections_file(d, is_ground_truth=False)

    acc_metrics: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for (image_name, label), true_df in ground_truth.groupby(['image_name', 'label']):
        pred_df: pd.DataFrame = detection_results.query('image_name == @image_name and label == @label')

        acc_metrics[label]['total_true'] += len(true_df)
        acc_metrics[label]['total_pred'] += len(pred_df)

        if (len(true_df) > 0) and (len(pred_df) == 0):
            acc_metrics[label]['false_negative'] += len(true_df)
            continue

        true_boxes: AbsoluteNDArrayBoxes = true_df[['left', 'top', 'right', 'bottom']].to_numpy()
        pred_boxes: AbsoluteNDArrayBoxes = pred_df[['left', 'top', 'right', 'bottom']].to_numpy()

        pairwise_iou: NDArray[Shape['* num_boxes1, * num_boxes2'], Float32] = compute_iou(
            boxes1=true_boxes,
            boxes2=pred_boxes,
        )

        used_rows, used_cols = set(), set()

        while True:
            argmax_row, argmax_col = np.unravel_index(indices=np.argmax(pairwise_iou), shape=pairwise_iou.shape)
            max_iou: float = pairwise_iou[argmax_row, argmax_col]

            if max_iou < t:
                break

            pairwise_iou[argmax_row, :] = float('-inf')
            pairwise_iou[:, argmax_col] = float('-inf')

            used_rows.add(argmax_row)
            used_cols.add(argmax_col)

            acc_metrics[label]['true_positive'] += 1

        acc_metrics[label]['false_negative'] += len(set(range(len(true_df))) - used_rows)
        acc_metrics[label]['false_positive'] += len(set(range(len(pred_df))) - used_cols)

    for label, metrics in acc_metrics.items():
        precision: float = metrics['true_positive'] / (metrics['true_positive'] + metrics['false_positive'])
        recall: float = metrics['true_positive'] / (metrics['true_positive'] + metrics['false_negative'])
        f1_score: float = 2 * (precision * recall) / (precision + recall)

        print(f'{label}:')
        print(f'\tPrecision: {precision:.2f}')
        print(f'\tRecall: {recall:.2f}')
        print(f'\tF1 score: {f1_score:.2f}')
        print()


if __name__ == '__main__':
    main()
