from src.parse import Config


def test_config_pads_levels_to_ten() -> None:
    config = Config(level=[{"id": 1, "width": 19, "height": 19}])

    assert len(config.level) == 10
    assert config.level[0] == {"id": 1, "width": 19, "height": 19}
    assert config.level[1] == {"id": 2, "width": 25, "height": 25}
    assert config.level[-1] == {"id": 10, "width": 31, "height": 31}
