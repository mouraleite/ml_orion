from types import SimpleNamespace

from app.core.user_identity import is_sienge_colab_registered


def test_esconde_por_sienge_id():
    users = [SimpleNamespace(sienge_id=10, cpf=None, email="a@x.com", full_name="A")]
    colab = SimpleNamespace(sienge_id=10, cpf=None, email="", name="Outro")
    assert is_sienge_colab_registered(colab, users) is True


def test_esconde_por_cpf_com_mascara_diferente():
    users = [SimpleNamespace(sienge_id=None, cpf="266.280.268-50", email="a@x.com", full_name="A")]
    colab = SimpleNamespace(sienge_id=99, cpf="26628026850", email="", name="Outro")
    assert is_sienge_colab_registered(colab, users) is True


def test_esconde_por_email():
    users = [SimpleNamespace(sienge_id=None, cpf=None, email="Fabio@mouraleite.com.br", full_name="A")]
    colab = SimpleNamespace(sienge_id=1, cpf="11111111111", email="fabio@mouraleite.com.br", name="Fabio")
    assert is_sienge_colab_registered(colab, users) is True


def test_esconde_por_nome_sem_cpf_no_sienge():
    users = [
        SimpleNamespace(
            sienge_id=None,
            cpf="266.280.268-50",
            email="alessandro@x.com",
            full_name="ALESSANDRO PUCCI DA CONCEICAO",
        )
    ]
    colab = SimpleNamespace(sienge_id=77, cpf=None, email="", name="Alessandro Pucci da Conceicao")
    assert is_sienge_colab_registered(colab, users) is True


def test_deixa_passar_pessoa_nova():
    users = [SimpleNamespace(sienge_id=1, cpf="111.111.111-11", email="a@x.com", full_name="Ana")]
    colab = SimpleNamespace(sienge_id=2, cpf="22222222222", email="b@x.com", name="Bruno")
    assert is_sienge_colab_registered(colab, users) is False
