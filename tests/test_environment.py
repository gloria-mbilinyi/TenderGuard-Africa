def test_project_environment():
    import httpx
    import langgraph
    import mcp
    import pydantic
    import pypdf

    assert mcp is not None
    assert langgraph is not None
    assert pydantic is not None
    assert httpx is not None
    assert pypdf is not None
