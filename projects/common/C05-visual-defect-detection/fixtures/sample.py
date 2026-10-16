from PIL import Image, ImageDraw
from shared_mvp.assets import root


def sample():
    directory = root('C05')
    normal = Image.new('L', (64, 64), 255)
    normal.save(directory / 'normal.png')
    defective = normal.copy()
    ImageDraw.Draw(defective).rectangle((10, 20, 14, 23), fill=0)
    defective.save(directory / 'defect.png')
    return {'data': {'images': [{'image_id': 'I1', 'asset_path': 'defect.png', 'width': 64, 'height': 64},
                                {'image_id': 'I2', 'asset_path': 'normal.png', 'width': 64, 'height': 64}],
                     'annotations': [{'image_id': 'I1', 'label': 'defect', 'boxes': [{'x': 10, 'y': 20, 'w': 5, 'h': 4}]},
                                     {'image_id': 'I2', 'label': 'normal', 'boxes': []}]},
            'params': {'image_id': 'I1'}}
