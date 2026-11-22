import httpx

from pipeline.sdmx import SdmxClient, build_key, parse_structure, urn_ref

URN = "urn:sdmx:org.sdmx.infomodel.codelist.Codelist="

STRUCTURE_V2 = {
    "data": {
        "dataflows": [{"id": "BOP", "agencyID": "IMF.STA", "version": "2.0.0",
                       "name": "Balance of Payments"}],
        "dataStructures": [
            {
                "id": "DSD_BOP",
                "dataStructureComponents": {
                    "dimensionList": {
                        "dimensions": [
                            {"id": "INDICATOR", "position": 1, "localRepresentation": {
                                "enumeration": URN + "IMF.STA:CL_IND(1.0.0)"}},
                            {"id": "COUNTRY", "position": 0, "localRepresentation": {
                                "enumeration": URN + "IMF:CL_COUNTRY(1.0.0)"}},
                            {"id": "FREQUENCY", "position": 2},
                        ]
                    },
                    "attributeList": {"attributes": [{"id": "OBS_STATUS"}, {"id": "UNIT_MULT"}]},
                },
            }
        ],
        "codelists": [
            {"id": "CL_IND", "agencyID": "IMF.STA",
             "codes": [{"id": "FA", "names": {"en": "Financial account"}}]},
            {"id": "CL_COUNTRY", "agencyID": "IMF",
             "codes": [{"id": "USA", "name": "United States"}, {"id": "NOR", "name": "Norway"}]},
            {"id": "CL_FREQ", "agencyID": "SDMX", "codes": [{"id": "Q", "name": "Quarterly"}]},
        ],
        "conceptSchemes": [
            {"id": "CS", "concepts": [{"id": "FREQUENCY", "coreRepresentation": {
                "enumeration": URN + "SDMX:CL_FREQ(2.1)"}}]}
        ],
    }
}


def test_urn_ref():
    assert urn_ref("urn:x.Codelist=IMF.STA:CL_IND(1.0.0)") == "IMF.STA:CL_IND"


def test_parse_structure_orders_dims_and_resolves_codelists():
    s = parse_structure(STRUCTURE_V2)
    assert [d.id for d in s.dimensions] == ["COUNTRY", "INDICATOR", "FREQUENCY"]
    country = s.find_dimension("COUNTRY", "REF_AREA")
    assert s.codes(country)["USA"] == "United States"
    assert s.codes(s.dimensions[1]) == {"FA": "Financial account"}
    # FREQUENCY has no local representation: falls back to the concept scheme
    assert s.codes(s.dimensions[2]) == {"Q": "Quarterly"}
    assert s.attributes == ["OBS_STATUS", "UNIT_MULT"]


def test_find_dimension_skips_counterpart():
    s = parse_structure(STRUCTURE_V2)
    s.dimensions[0].id = "COUNTERPART_COUNTRY"
    assert s.find_dimension("COUNTRY") is None


def test_build_key():
    s = parse_structure(STRUCTURE_V2)
    vals = {"COUNTRY": "USA", "FREQUENCY": "Q"}
    assert build_key(s.dimensions, vals, "*") == "USA.*.Q"
    assert build_key(s.dimensions, vals) == "USA..Q"


def test_client_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert request.headers["User-Agent"].startswith("cf-global-capital-flows")
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    client = SdmxClient("https://example.org/sdmx", transport=httpx.MockTransport(handler),
                        sleep=lambda _s: None)
    resp = client.get("data/x", accept="application/json")
    assert resp.status_code == 200 and calls["n"] == 3


def test_client_gives_up_after_max_retries():
    client = SdmxClient("https://example.org", max_retries=2,
                        transport=httpx.MockTransport(lambda r: httpx.Response(429)),
                        sleep=lambda _s: None)
    assert client.get("x").status_code == 429
