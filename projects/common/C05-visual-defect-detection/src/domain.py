from PIL import Image
from shared_mvp.assets import read, validate_images
from shared_mvp.domain import eid, require, result


def validate(data):
    validate_images('C05', data)
    ids = {i['image_id'] for i in data['images']}
    for label in data['annotations']:
        require(label['image_id'] in ids, 'Unknown annotation image')
        require(label['label'] in {'normal', 'defect'}, 'Unsupported annotation label')
        image = next(i for i in data['images'] if i['image_id'] == label['image_id'])
        for box in label['boxes']:
            require(box['x'] + box['w'] <= image['width'] and box['y'] + box['h'] <= image['height'], 'Annotation box outside image')


def validate_params(data, params):
    require(any(i['image_id'] == params['image_id'] for i in data['images']), 'Unknown image')


def compute(data, params):
    record = next(i for i in data['images'] if i['image_id'] == params['image_id'])
    ref = eid('C05', 'images', record['image_id'])
    image = read('C05', record)
    if image.size != (64, 64):
        return result({'predicted_label': 'uncertain', 'regions': [], 'needs_review': True, 'confidence_score': None, 'evidence_ids': [ref]}, 'unsupported_dimensions', {ref})
    mask = image.convert('L').point(lambda value: 255 if value < 32 else 0)
    box = mask.getbbox()
    regions = [] if box is None else [{'x': box[0], 'y': box[1], 'w': box[2] - box[0], 'h': box[3] - box[1]}]
    return result({'predicted_label': 'missing_component' if box else 'meal_complete', 'regions': regions, 'needs_review': bool(box), 'confidence_score': None, 'evidence_ids': [ref]}, authorized={ref})


def validate_output(output, run):
    require(output['predicted_label'] in {'meal_complete', 'missing_component', 'uncertain'}, 'Unsupported prediction label')
    require(output['confidence_score'] is None, 'C05 MVP does not have a calibrated confidence score')
    source = next(e['source_excerpt'] for e in run['evidence'] if e['collection'] == 'images')
    require(output['evidence_ids'] == [source and 'C05:images:' + source['image_id']], 'Prediction must cite only image evidence')
    require(bool(output['evidence_ids']), 'Image prediction requires image evidence')
    for box in output['regions']:
        require(box['x'] >= 0 and box['y'] >= 0 and box['w'] > 0 and box['h'] > 0, 'Predicted box must have positive size')
        require(box['x'] + box['w'] <= source['width'] and box['y'] + box['h'] <= source['height'], 'Predicted box outside image')
    require(output['needs_review'] or output['predicted_label'] == 'meal_complete', 'Unsupported or missing result requires review')
