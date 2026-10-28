from app.modules.detection.collectors.heuristics import pick_primary_gpu, storage_type_from_msft


def test_prefers_dedicated_gpu_over_integrated_listed_first():
    names = ["Intel(R) UHD Graphics 630", "NVIDIA GeForce RTX 3060"]
    assert pick_primary_gpu(names) == "NVIDIA GeForce RTX 3060"


def test_ignores_virtual_display_adapters():
    names = [
        "Microsoft Basic Display Adapter",
        "Parsec Virtual Display Adapter",
        "AMD Radeon RX 6600",
    ]
    assert pick_primary_gpu(names) == "AMD Radeon RX 6600"


def test_falls_back_to_integrated_gpu_when_it_is_the_only_one():
    assert pick_primary_gpu(["AMD Radeon(TM) Graphics"]) == "AMD Radeon(TM) Graphics"


def test_no_usable_gpu_returns_none():
    assert pick_primary_gpu([None, "  ", "Microsoft Basic Display Adapter"]) is None


def test_storage_type_mapping():
    assert storage_type_from_msft(media_type=4, bus_type=17) == "NVME_SSD"
    assert storage_type_from_msft(media_type=4, bus_type=11) == "SATA_SSD"
    assert storage_type_from_msft(media_type=3, bus_type=11) == "HDD"
    # HDDs antigos costumam informar MediaType 0: melhor "não sei" do que chutar.
    assert storage_type_from_msft(media_type=0, bus_type=11) is None
