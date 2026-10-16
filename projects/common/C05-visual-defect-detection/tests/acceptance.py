def happy(test, run):
    test.assertEqual(run['baseline_result']['predicted_label'], 'missing_component')
    test.assertEqual(run['baseline_result']['regions'], [{'x': 10, 'y': 20, 'w': 5, 'h': 4}])
    test.assertTrue(all(e['collection'] != 'annotations' for e in run['evidence']))


def edges(test, execute, sample):
    sample['params']['image_id'] = 'I2'
    test.assertEqual(execute(sample)['baseline_result']['predicted_label'], 'meal_complete')
    sample['data']['images'][0]['asset_path'] = '../secret.png'
    test.assertEqual(execute(sample, expected_http=422), 422)
