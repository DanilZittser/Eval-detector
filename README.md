# Eval detector

Evaluates an object detectors detections against ground truth.

### Environment setup
```bash
git clone git@github.com:DanilZittser/Eval-detector.git
cd Eval-detector
python3 -m venv venv
source venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

### Run
```bash
./eval_detector -g assets/examples/ground-truth.txt -d assets/examples/detection-results.txt -t 0.5
```
- `-g` - path to ground truth file
- `-d` - path to detection results file
- `-t` - threshold for IoU

Ground truth file format:
```
<image file> <bounding box in form L,T,R,B> <object type>
```

Detection results file format:
```
<image file> <bounding box in form L,T,R,B> <object type> <float confidence 0-1>
```

Output example:
```
+---------+-------------+----------+------------+
|         |   precision |   recall |   f1_score |
|---------+-------------+----------+------------|
| apple   |        0.83 |     0.62 |       0.71 |
| banana  |        0.56 |     0.5  |       0.53 |
| coconut |        0.72 |     0.46 |       0.56 |
+---------+-------------+----------+------------+
```
