import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.backends.cudnn as cudnn
from numpy import random


from torchvision import transforms
from models.experimental import attempt_load
from utils.datasets import letterbox
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path
from utils.plots import plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized, TracedModel


def label_video():
    cap = cv2.VideoCapture(0)
    # VideoWriter for saving the video
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    #out = cv2.VideoWriter('ice_skating_output.mp4', fourcc, 30.0, (int(cap.get(3)), int(cap.get(4))))
    while cap.isOpened():
        (ret, frame) = cap.read()
        #print(np.shape(frame))
        if ret == True:
            img = frame
            weights = 'yolov7\yolov7.pt'
            imgsz = 128

            # Initialize
            device = select_device('cpu')
            half = device.type != 'cpu'  # half precision only supported on CUDA
            # Load model
            model = attempt_load(weights, map_location=device)  # load FP32 model
            stride = int(model.stride.max())  # model stride
            imgsz = check_img_size(imgsz, s=stride)  # check img_size

            if half:
                model.half() # to FP16

            # Get names and colors
            names = model.module.names if hasattr(model, 'module') else model.names
            colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]

            # Run inference
            if device.type != 'cpu':
                model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
            old_img_w = old_img_h = imgsz
            old_img_b = 1


            im0 = img.copy()

            # Stack
            img = [letterbox(img,imgsz)[0]]
            img = np.stack(img, 0)
            # Convert
            img = img[:, :, :, ::-1].transpose(0, 3, 1, 2)  # BGR to RGB, to bsx3x416x416
            img = np.ascontiguousarray(img, dtype=np.float16)

            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            #img = img.cuda()

            # Warmup
            if (old_img_b != img.shape[0] or old_img_h != img.shape[2] or old_img_w != img.shape[3]):
                old_img_b = img.shape[0]
                old_img_h = img.shape[2]
                old_img_w = img.shape[3]
                for i in range(3):
                    model(img)[0]

                # Inference
                with torch.no_grad():   # Calculating gradients would cause a GPU memory leak
                    pred = model(img)[0]

                # Apply NMS
                pred = non_max_suppression(pred, 0.3, 0.9)

                # Apply Classifier
                #pred = apply_classifier(pred, modelc, img, im0)

                # Process detections
                for i, det in enumerate(pred):  # detections per image
                    #gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                    if len(det):
                        # Rescale boxes from img_size to im0 size
                        det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                        # Write results
                        for *xyxy, conf, cls in reversed(det):
                            # Add bbox to image
                            label = f'{names[int(cls)]} {conf:.2f}'
                            plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=1)

                    # Print time (inference + NMS)
                    #print(f'{s}Done. ({(1E3 * (t2 - t1)):.1f}ms) Inference, ({(1E3 * (t3 - t2)):.1f}ms) NMS')

                    # Stream results
                #cv2.imshow(im0)
                im0 = cv2.resize(im0, (960, 720))
                cv2.imshow('label', im0)
                #cv2.waitKey(1)  # 1 millisecond

            #out.write(frame)
        else:
            break

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    cap.release()
    #out.release()
    cv2.destroyAllWindows()


label_video()