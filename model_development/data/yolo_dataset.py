# Subclass of data.Dataset, just to wrap the __getitem__ method to return YOLO format!
from data.dataset import CustomDataset
from data.image_processor import ImageProcessor
from data.dataloader_builder import DataLoaderBuilder
import random
import shutil
import os
import cv2

class YoloDataset(CustomDataset):
  def __init__(self, dataset_name, root_dir, subfolder_sampling_ratios, augmentations=[]):
    super().__init__(dataset_name, root_dir, subfolder_sampling_ratios, augmentations)
    self.classes = {0: 'shark'} # single class object detection

  def construct_classes(self):
    # for multiclass, return a list of classes and names it maps to
    pass

  def _to_yolo(self, bboxes):
    """
    input: bbox: [[xmin, ymin, xmax, ymax], ...]
    output: [[class, x_center, y_center, width, height], ...]
    """
    yolo_bboxes = []
    for bbox in bboxes:
      xmin, ymin, xmax, ymax = bbox
      width, height = xmax - xmin, ymax - ymin
      x_center, y_center = xmin + width / 2, ymin + height / 2
      yolo_bboxes.append([0, x_center, y_center, width, height])
    return yolo_bboxes
  
  def __getitem__(self, idx):
    # Use the parent class's __getitem__ method to get the image and annotations
    # and update the annotations to be in YOLO format
    istance = super().__getitem__(idx)
    image, bboxes = istance['image'], istance['boxes']
    normalised_bboxes = ImageProcessor.normalise_bbox(bboxes, image)
    yolo_bboxes = self._to_yolo(normalised_bboxes)
    return {"image": image, "boxes": yolo_bboxes}
  
  def build(self):
    """
    Yolo wants the data to be stored in a specific folder structure and to pass
    the path. We could do wiht a dataloader but this approach is leaner.
    """
    dataset_path = os.path.join(self.experimentation_dataset_path, self.dataset_name)
    if self.dataset_name not in os.listdir(self.experimentation_dataset_path):
      try:
        train_ratio, val_ratio, test_ratio = DataLoaderBuilder.get_split_ratios()
        print(f'Building dataset {self.dataset_name} in {dataset_path} by copying {len(self)} images...')
        # Build dataset by randomly sampling len(self) * {train/val/test}_ratio images from each subfolder
        # and copying them to the dataset_path.
        # The folder structure should be:
        # dataset_path
        # ├── train
        # │   ├── images
        # │   └── labels
        # ├── val
        # │   ├── images
        # │   └── labels
        # └── test
        #     ├── images
        #     └── labels
        # Consider that you can get image and label by doing self[i]['image'] and self[i]['boxes']
        # the boxes have the yolo structure and should be converted in txt files with the same name as the image
        # and stored in the labels folder

        # Create dataset folder
        os.mkdir(dataset_path)
        # Create subfolders
          
        # Calculate indices for train, val and test
        indices = list(range(len(self)))
        random.shuffle(indices)
        train_size = int(train_ratio * len(self))
        val_size = int(val_ratio * len(self))
        test_size = len(self) - train_size - val_size
        split = {
          'train': indices[:train_size],
          'val': indices[train_size:train_size+val_size],
          'test': indices[train_size+val_size:]
        }

        subfolders = ['train', 'val', 'test']
        for subfolder in subfolders:
          print(f'Creating subfolder {subfolder} of size {len(split[subfolder])} ...')
          os.mkdir(os.path.join(dataset_path, subfolder))
          os.mkdir(os.path.join(dataset_path, subfolder, 'images'))
          os.mkdir(os.path.join(dataset_path, subfolder, 'labels'))

          # Copy images and create labels
          # Note that when we get an image, we perform augmentations and get back the 
          # augmented image and relative bboxes. Therefore, we need to copy the augmented image
          # not, the original.
          # However, if augmentation is [], then we don't perform any augmentation,
          # so we can directly use shutil.copyfile
          for i in split[subfolder]:
            image, bboxes = self[i]['image'], self[i]['boxes']
            image_path = self.image_paths[i]
            image_id = os.path.basename(image_path)
            new_image_path = os.path.join(dataset_path, subfolder, 'images', image_id)
            if len(self.augmentations) > 0:
              # Write image represented by numpy tensor to new_image_path
              cv2.imwrite(new_image_path, image)
            else:
              # simply copy original image
              shutil.copyfile(image_path, new_image_path)

            # Create label
            label_path = os.path.splitext(image_path)[0] + '.txt'
            with open(label_path, 'w') as f:
              for bbox in bboxes:
                f.write(' '.join([str(round(b, 4)) for b in bbox]) + '\n')

        # Add data_config.yaml file with Yolo Format
        with open(os.path.join(dataset_path, 'data_config.yaml'), 'w') as f:
          f.write(f"path: {dataset_path}")
          f.write(f"train: ./train")
          f.write(f"val: ./val")
          f.write(f"test: ./test")
          f.write(f"names:")
          for class_id, class_name in self.classes.items():
            f.write(f"  {class_id}: {class_name}")
          
      except Exception as e:
        print(f'Error while building dataset {self.dataset_name}: {e}')
        shutil.rmtree(dataset_path)
        raise e
    else:
      print('Dataset already exists, skipping building step')

    return dataset_path

        


    



