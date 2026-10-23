"""Tests for Universal Domain Schema and Item Extractor."""
from syntra.agents.fullstack_generator import (
    extract_universal_domain,
    generate_backend_package,
    generate_marvelous_frontend_spa,
    parse_prompt_categories_and_items,
)


def test_stop_words_never_become_entity_name():
    """Verify that verbs and stop words like 'Build', 'Create', 'Make' NEVER become entities."""
    test_prompts = [
        ("Build a modern asset tracking system", "Asset"),
        ("Create an interactive dashboard for managing fleet vehicles", "FleetVehicle"),
        ("Make a fullstack application for hospital patient records", "PatientRecord"),
        ("Develop an interactive real estate portal with villa listings", "PropertyListing"),
        ("Implement a high-performance crypto portfolio tracker", "CryptoAsset"),
        ("Build a rich workout planner for athletic training", "WorkoutRoutine"),
        ("Create an e-commerce catalog for audio equipment", "ProductItem"),
        ("Build an interactive satellite orbit monitoring system", "Satellite"),
    ]

    for prompt, expected_entity in test_prompts:
        domain = extract_universal_domain(prompt)
        assert domain["entity_name"] != "Build", f"Failed on prompt: {prompt}"
        assert domain["entity_name"] != "Create", f"Failed on prompt: {prompt}"
        assert domain["entity_name"] != "Make", f"Failed on prompt: {prompt}"
        assert domain["entity_name"] != "Develop", f"Failed on prompt: {prompt}"
        assert domain["entity_name"] == expected_entity, f"Expected {expected_entity}, got {domain['entity_name']} for '{prompt}'"


def test_parse_prompt_categories_and_items_from_markdown():
    """Verify that categories and items specified in prompt markdown are accurately extracted."""
    prompt = """
    ### Scale: 6 Categories with 3 items each
    1. Signature Appetizers (3 items)
       - Crispy Truffle Arancini
       - Yellowtail Jalapeno Sashimi
       - Wood-Fired Artichoke Dip

    2. Artisan Pastas (3 items)
       - Wild Mushroom Pappardelle
       - Squid Ink Tagliolini
       - Classic Cacio e Pepe

    3. Craft Beverages (3 items)
       - Smoked Rosemary Old Fashioned
       - Hibiscus Sparkling Cooler
       - Nitro Cold Brew Float
    """
    cats, items = parse_prompt_categories_and_items(prompt)
    assert len(cats) == 3
    assert "Signature Appetizers" in cats
    assert "Artisan Pastas" in cats
    assert "Craft Beverages" in cats
    assert len(items) == 9

    domain = extract_universal_domain(prompt)
    assert len(domain["category_options"]) == 3
    assert len(domain["seed_items"]) == 9
    assert domain["seed_items"][0]["title"] == "Crispy Truffle Arancini"
    assert domain["seed_items"][0]["category"] == "Signature Appetizers"


def test_brand_name_extraction():
    """Verify that quoted brand names are extracted and applied to domain profile."""
    prompt = 'Create an interactive menu for "Luigi\'s Artisanal Trattoria" with pastas and pizzas'
    domain = extract_universal_domain(prompt)
    assert domain.get("brand_name") == "Luigi's Artisanal Trattoria"
    assert domain["is_restaurant"] is True


def test_backend_and_spa_generation_universal():
    """Verify that generate_backend_package and generate_marvelous_frontend_spa work for any domain."""
    prompt = "Build a cryptocurrency portfolio tracker with Bitcoin, Ethereum, and Solana"
    backend = generate_backend_package(prompt)
    assert "CryptoAssetModel" in backend["models.py"]
    assert "CryptoAssetCreate" in backend["schemas.py"]
    assert "test_health_check" in backend["test_api.py"]

    spa = generate_marvelous_frontend_spa(prompt)
    assert "<!DOCTYPE html>" in spa
    assert "</html>" in spa
    assert "Crypto Assets" in spa
    assert "// TODO" not in spa
