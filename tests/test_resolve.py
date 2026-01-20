from simage.core.resolve import norm_kind

def test_norm_kind_variants():
    assert norm_kind('checkpoint') == 'checkpoint'
    assert norm_kind('model') == 'checkpoint'
    assert norm_kind('ckpt') == 'checkpoint'
    assert norm_kind('lora') == 'lora'
    assert norm_kind('locon') == 'lora'
    assert norm_kind('lycoris') == 'lora'
    assert norm_kind('embedding') == 'embedding'
    assert norm_kind('textualinversion') == 'embedding'
    assert norm_kind('vae') == 'vae'
    assert norm_kind('controlnet') == 'controlnet'
    assert norm_kind('upscaler') == 'upscaler'
    assert norm_kind('unknown') is None
    assert norm_kind(None) is None
