from simage.core.resources import as_float, classify_urn

def test_as_float_valid():
    assert as_float('1.23') == 1.23
    assert as_float(2) == 2.0
    assert as_float(None) is None
    assert as_float('not_a_float') is None

def test_classify_urn():
    assert classify_urn('urn:air:sdxl:checkpoint:civitai:foo') == 'checkpoint'
    assert classify_urn('urn:air:sdxl:lora:civitai:foo') == 'lora'
    assert classify_urn('urn:air:sdxl:embedding:civitai:foo') == 'embedding'
    assert classify_urn('urn:air:sdxl:vae:civitai:foo') == 'vae'
    assert classify_urn('urn:air:sdxl:upscaler:civitai:foo') == 'upscaler'
    assert classify_urn('urn:air:sdxl:controlnet:civitai:foo') == 'controlnet'
    assert classify_urn('urn:air:sdxl:other:civitai:foo') is None
