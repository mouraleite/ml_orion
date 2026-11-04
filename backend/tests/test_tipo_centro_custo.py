from app.services.tipo_centro_custo import codigo_tipo_sienge, rotulo_tipo_sienge


def test_mapeia_codigos_1_a_4():
    assert rotulo_tipo_sienge("1") == "Obra e Centro de Custo"
    assert rotulo_tipo_sienge(2) == "Somente Obra"
    assert rotulo_tipo_sienge("3") == "Somente Centro de Custo"
    assert rotulo_tipo_sienge("4") == "Centro de Custo associado à Obra"


def test_preserva_rotulo_ja_traduzido():
    assert rotulo_tipo_sienge("Somente Obra") == "Somente Obra"
    assert rotulo_tipo_sienge("Centro de Custo associado à Obra") == "Centro de Custo associado à Obra"


def test_objeto_sienge_usa_id_e_ignora_icone():
    bruto = {
        "id": 2,
        "description": "Building",
        "icon": "https://cdn.sienge.com.br/icons/building.png",
        "src": "/file.svg",
    }
    assert codigo_tipo_sienge(bruto) == "2"
    assert rotulo_tipo_sienge(bruto) == "Somente Obra"


def test_html_img_e_url_nao_passam():
    assert rotulo_tipo_sienge('<img src="https://x/a.png">') == "Desconhecido"
    assert rotulo_tipo_sienge("https://cdn.sienge.com.br/type/2.png") == "Desconhecido"
    assert rotulo_tipo_sienge("/window.svg") == "Desconhecido"
    assert "<" not in rotulo_tipo_sienge("<img src=x>")
    assert "src" not in rotulo_tipo_sienge("<img src=x onerror=alert(1)>")


def test_vazio_usa_default():
    assert rotulo_tipo_sienge(None) == "Desconhecido"
    assert rotulo_tipo_sienge("") == "Desconhecido"
    assert rotulo_tipo_sienge(None, default="Somente Obra") == "Somente Obra"
    assert codigo_tipo_sienge(None) == ""
