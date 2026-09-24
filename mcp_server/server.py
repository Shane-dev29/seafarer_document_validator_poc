import sys
from mcp.server.mcpserver import MCPServer
from mcp_server.registry_service import registry_service

# Initialize MCP Server
app = MCPServer("seafarer-verifier-registry")

@app.tool()
def has_verifier(country: str) -> bool:
    """Check if an automated verification script is already cached for this country/nationality."""
    return registry_service.has_verifier(country)

@app.tool()
def list_available_verifiers() -> list:
    """List all nationalities/countries that currently have ready-to-run verification scripts."""
    return registry_service.list_verifiers()

@app.tool()
def run_verifier(
    country: str,
    nationality: str,
    full_name: str = "",
    dob: str = "",
    coc_number: str = "",
    cdc_number: str = "",
    foc_number: str = "",
    headless: bool = True
) -> dict:
    """
    Execute the existing cached verifier for a seafarer.
    Avoids re-scraping and runs browser automation directly on the portal.
    """
    profile_data = {
        "full_name": full_name,
        "nationality": nationality or country,
        "dob": dob,
        "coc_number": coc_number,
        "cdc_number": cdc_number,
        "foc_number": foc_number
    }
    return registry_service.run_verifier(country, profile_data, headless=headless)

@app.tool()
def register_new_verifier(country: str, python_code: str) -> dict:
    """
    Register a newly generated verification script for a newly encountered nationality.
    Once registered, this nationality will never need to be scraped or generated again.
    """
    return registry_service.register_verifier(country, python_code)

if __name__ == "__main__":
    app.run()
