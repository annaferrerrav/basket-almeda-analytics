# -*- coding: utf-8 -*-
"""
Tests de la capa de dades i mètriques.

La majoria corren contra els fitxers reals de 25-26: si algun dia un Excel canvia
d'estructura, aquests tests ho han de petar abans que no ho faci l'app.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from almeda_pbp import config as cfg, metriques as m
from almeda_pbp.carrega import carrega_pbp, filtra
from almeda_pbp.normalitza import ALIES_DESENLLAC, ALIES_TACTICA, normalitza_jugadora, normalitza_serie


@pytest.fixture(scope="module")
def dades():
    resultat = carrega_pbp()
    if resultat.dades.empty:
        pytest.skip("No hi ha fitxers PBP al repositori")
    return resultat


# --- Normalització --------------------------------------------------------

def test_alies_tactica_unifica_variants():
    serie = pd.Series(["contratac", "Contraatac", "CONTRATAC", "2mano", "2 Mano"])
    valors, desconeguts = normalitza_serie(serie, ALIES_TACTICA)
    assert list(valors[:3]) == ["Contratac"] * 3
    assert list(valors[3:]) == ["2 Mano"] * 2
    assert not desconeguts.any()


def test_buits_no_son_desconeguts():
    """Un "-" vol dir "aquí no aplica": ha de ser None, no una incidència."""
    serie = pd.Series(["-", "", None, float("nan")])
    valors, desconeguts = normalitza_serie(serie, ALIES_DESENLLAC)
    assert valors.isna().all()
    assert not desconeguts.any()


def test_valor_desconegut_es_conserva_i_es_marca():
    """No s'endevina mai: el valor rar es manté tal qual i es marca per revisar."""
    serie = pd.Series(["t23f"])
    valors, desconeguts = normalitza_serie(serie, ALIES_DESENLLAC)
    assert valors.iloc[0] == "t23f"
    assert desconeguts.iloc[0]


def test_noms_jugadora_unifiquen_caixa_i_accent():
    serie = pd.Series(["Jové", "jové", "jove", "TIERNO", "tierno"])
    assert list(normalitza_jugadora(serie)) == ["Jové", "Jové", "Jové", "Tierno", "Tierno"]


# --- Càrrega --------------------------------------------------------------

def test_columnes_originals_es_mantenen(dades):
    """Els noms de columna dels Excel no es tradueixen: cap sorpresa per l'analista."""
    for columna in (cfg.COL_TACTICA, cfg.COL_DESENLLAC, *cfg.COLS_QUINTET, cfg.COL_PF, cfg.COL_PC):
        assert columna in dades.dades.columns


def test_no_hi_ha_jornades_duplicades(dades):
    """Dos fitxers per a la mateixa jornada duplicarien totes les jugades."""
    per_fitxer = dades.dades.groupby([cfg.COL_TEMPORADA, cfg.COL_JORNADA])[cfg.COL_FITXER].nunique()
    assert (per_fitxer == 1).all()


def test_punts_son_enters_no_nuls(dades):
    for columna in (cfg.COL_PF, cfg.COL_PC):
        assert dades.dades[columna].notna().all()
        assert pd.api.types.is_integer_dtype(dades.dades[columna])


def test_ordre_cronologic_es_el_del_fitxer(dades):
    """
    `Minut` és el minut RESTANT i decreix dins de cada període: ordenar-lo
    ascendentment invertiria el partit. Es comprova que dins d'un període l'ordre
    del fitxer va de més minuts restants a menys.
    """
    una = dades.dades[dades.dades[cfg.COL_JORNADA] == dades.dades[cfg.COL_JORNADA].iloc[0]]
    for _, periode in una.groupby(cfg.COL_PERIODE):
        minuts = periode.sort_values(cfg.COL_ORDRE)[cfg.COL_MINUT].dropna()
        assert minuts.is_monotonic_decreasing


def test_quintet_sense_substitucions_es_invalida():
    """
    Un fitxer real de 4 períodes sempre té substitucions. Si una posició és
    sempre la mateixa jugadora (o sempre buida) a totes les jugades, és que
    l'extracció automàtica no ha capturat els canvis: es descarta el quintet
    d'aquest fitxer sencer (les 5 columnes), no només la posició buida.
    """
    from almeda_pbp.carrega import Incidencia, _comprova_quintet

    n = 25  # per damunt del llindar de mostra mínima (20 files)
    df = pd.DataFrame(
        {
            "jug 1": ["Ivet"] * n, "jug 2": ["Tierno"] * n, "jug 3": ["Cojo"] * n,
            "jug 4": ["Dana"] * n, "jug 5": [None] * n,
        }
    )
    incidencies: list[Incidencia] = []
    _comprova_quintet(df, "25-26", 23, Path("fals.xlsx"), incidencies)

    assert len(incidencies) == 1
    assert incidencies[0].tipus == "Quintet no fiable"
    assert df[cfg.COLS_QUINTET].isna().all().all()


def test_quintet_amb_rotacions_normal_no_es_toca():
    """
    Un quintet amb rotacions normals no ha de disparar cap incidència.
    Cal que TOTES les posicions rotin: n'hi ha prou que una sola es quedi
    fixa perquè es consideri sospitós (com passa a la pràctica: quan falla
    l'extracció, sol fallar per a tot el quintet, no per a una sola posició).
    """
    from almeda_pbp.carrega import Incidencia, _comprova_quintet

    n = 25
    df = pd.DataFrame(
        {
            "jug 1": ["Ivet"] * 15 + ["Tierno"] * 10,
            "jug 2": ["Tierno"] * 15 + ["Ivet"] * 10,
            "jug 3": ["Cojo"] * 12 + ["Dana"] * 13,
            "jug 4": ["Dana"] * 12 + ["Cojo"] * 13,
            "jug 5": ["Puyi"] * 20 + ["Bernal"] * 5,
        }
    )
    incidencies: list[Incidencia] = []
    _comprova_quintet(df, "25-26", 1, Path("fals.xlsx"), incidencies)

    assert incidencies == []
    assert df["jug 1"].notna().all()


def test_quintet_amb_mostra_petita_no_es_comprova():
    """Amb poques files no es pot distingir 'no hi ha hagut canvis' d'error."""
    from almeda_pbp.carrega import Incidencia, _comprova_quintet

    df = pd.DataFrame({c: ["X"] * 5 for c in cfg.COLS_QUINTET})
    incidencies: list[Incidencia] = []
    _comprova_quintet(df, "25-26", 1, Path("fals.xlsx"), incidencies)

    assert incidencies == []
    assert df["jug 1"].notna().all()


# --- Mètriques ------------------------------------------------------------

def test_plus_minus_quadra_amb_el_diferencial(dades):
    """
    Identitat de control: com que hi ha 5 jugadores en pista a cada jugada, la
    suma de tots els +/- individuals ha de ser 5 x (PF total - PC total).
    Si això falla, o el +/- o la lectura de PF/PC estan malament.

    Restringit a les files amb quintet complet: files sense cap jugadora
    anotada (plantilles buides al final d'un fitxer, sempre amb PF=PC=0, per
    tant inofensives) o amb el quintet invalidat per `_comprova_quintet`
    (font automàtica sense substitucions detectades) no aporten 5 crèdits i
    trencarien la identitat sense que sigui un error real.
    """
    complet = dades.dades.dropna(subset=cfg.COLS_QUINTET)
    esperat = 5 * (complet[cfg.COL_PF].sum() - complet[cfg.COL_PC].sum())
    assert m.plus_minus_individual(complet)["+/-"].sum() == esperat


def test_plus_minus_no_usa_diff():
    """
    PF i PC ja són l'increment de la jugada, no un marcador acumulat.
    Amb dues jugades de 2 punts cadascuna, el +/- ha de ser +4, no +2.
    """
    df = pd.DataFrame(
        {
            "jug 1": ["A", "A"], "jug 2": ["B", "B"], "jug 3": ["C", "C"],
            "jug 4": ["D", "D"], "jug 5": ["E", "E"],
            cfg.COL_PF: [2, 2], cfg.COL_PC: [0, 0],
        }
    )
    assert m.plus_minus_individual(df).set_index("Jugadora").loc["A", "+/-"] == 4


def test_parelles_generen_les_deu_combinacions():
    df = pd.DataFrame(
        {
            "jug 1": ["A"], "jug 2": ["B"], "jug 3": ["C"], "jug 4": ["D"], "jug 5": ["E"],
            cfg.COL_PF: [3], cfg.COL_PC: [1],
        }
    )
    parelles = m.plus_minus_parelles(df, min_jugades=1)
    assert len(parelles) == 10
    assert (parelles["+/-"] == 2).all()


def test_plus_minus_per_posicio_reparteix_el_total(dades):
    """
    Desglossar per posició no pot crear ni perdre jugades: la suma de jugades per
    (jugadora, posició) ha de ser igual a la suma del +/- individual.
    """
    df = dades.dades
    total_individual = m.plus_minus_individual(df)["Jugades"].sum()
    total_posicio = m.plus_minus_per_posicio(df, min_jugades=1)["Jugades"].sum()
    assert total_individual == total_posicio


def test_parelles_per_posicio_respecten_la_posicio():
    """
    La parella de posicions no és la parella de noms: A de base amb B de pivot
    ha de comptar a «jug 1 · jug 5», no a totes les combinacions on surtin.
    """
    df = pd.DataFrame(
        {
            "jug 1": ["A"], "jug 2": ["B"], "jug 3": ["C"], "jug 4": ["D"], "jug 5": ["E"],
            cfg.COL_PF: [5], cfg.COL_PC: [1],
        }
    )
    taula = m.plus_minus_parelles_posicio(df, min_jugades=1)
    # Set 7 parelles configurades, cadascuna una sola vegada, totes amb +4.
    assert len(taula) == len(cfg.PARELLES_POSICIO)
    assert (taula["+/-"] == 4).all()
    fila = taula[taula["Parella posicions"] == "jug 1 · jug 5"].iloc[0]
    assert (fila["Jugadora A"], fila["Jugadora B"]) == ("A", "E")


def test_rebot_ignora_columnes_sense_cap_valor():
    """Una columna que ningú ha omplert no ha de sortir com una fila de zeros."""
    df = pd.DataFrame(
        {
            cfg.COL_PERIODE: [1, 2],
            "RO a favor": [1.0, 2.0],
            "RD a favor": [None, None],
            cfg.COL_PF: [0, 0], cfg.COL_PC: [0, 0],
        }
    )
    taula = m.resum_rebot_ofensiu(df)
    assert "RO a favor" in taula.columns
    assert "RD a favor" not in taula.columns
    assert taula.loc[taula[cfg.COL_PERIODE] == "Total", "RO a favor"].iloc[0] == 3.0


def test_valor_no_numeric_al_rebot_es_reporta(dades):
    """El «3?» de la j4 s'ha de veure a incidències, no desaparèixer en un coerce."""
    tipus = dades.taula_incidencies["Tipus"]
    if "Valor no numèric" in set(tipus):
        detall = dades.taula_incidencies.loc[tipus == "Valor no numèric", "Detall"].iloc[0]
        assert "«" in detall and "columna" in detall
    for columna in cfg.COLS_REBOT:
        if columna in dades.dades.columns:
            assert pd.api.types.is_numeric_dtype(dades.dades[columna])


def test_divisio_per_zero_no_peta():
    """Un sistema sense cap tir no pot donar NaN ni infinit al % de conversió."""
    df = pd.DataFrame(
        {
            cfg.COL_TACTICA: ["Play"], cfg.COL_DESENLLAC: ["Pèrdua"],
            "jug 1": ["A"], "jug 2": ["B"], "jug 3": ["C"], "jug 4": ["D"], "jug 5": ["E"],
            cfg.COL_PF: [0], cfg.COL_PC: [0],
        }
    )
    resum = m.resum_sistemes(df)
    assert resum["% conversió"].iloc[0] == 0
    assert resum["Punts/jugada"].notna().all()


def test_punts_anotats_i_assistits_no_es_sumen():
    """
    Una jugada on A assisteix i B anota 2 punts ha de donar 2 punts anotats a B
    i 2 punts generats a A: 4 en total seria doble comptatge.
    """
    df = pd.DataFrame(
        {
            cfg.COL_TACTICA: ["Play"], cfg.COL_DESENLLAC: ["T2C"],
            cfg.COL_FINALITZADORA: ["B"], cfg.COL_ASSIST: ["A"],
            "jug 1": ["A"], "jug 2": ["B"], "jug 3": ["C"], "jug 4": ["D"], "jug 5": ["E"],
            cfg.COL_PF: [2], cfg.COL_PC: [0],
        }
    )
    taula = m.punts_i_assistencies_per_sistema(df).set_index("Jugadora")
    assert taula.loc["B", "Punts anotats"] == 2
    assert taula.loc["B", "Punts assistits"] == 0
    assert taula.loc["A", "Punts anotats"] == 0
    assert taula.loc["A", "Punts assistits"] == 2


# --- Informe PDF ----------------------------------------------------------

def test_informe_genera_un_pdf_valid(dades):
    from almeda_pbp import informe

    sistemes = m.resum_sistemes(dades.dades).head(2)[cfg.COL_TACTICA].tolist()
    contingut = informe.genera_informe(dades.dades, sistemes, {"temporada": "25-26"})
    assert contingut.startswith(b"%PDF")
    assert len(contingut) > 10_000  # amb gràfics dins, un PDF buit seria molt més petit


def test_informe_amb_seleccio_buida_no_peta(dades):
    """Sense cap sistema seleccionat l'informe s'ha de generar igualment, amb l'avís."""
    from almeda_pbp import informe

    contingut = informe.genera_informe(dades.dades.iloc[0:0], [], {})
    assert contingut.startswith(b"%PDF")


# --- Scraping i magatzem --------------------------------------------------

def test_lletra_del_grup():
    from almeda_pbp.feb.calendari import _lletra_del_grup

    assert _lletra_del_grup('Liga Regular "A"') == "A"
    assert _lletra_del_grup('Liga Regular "B"') == "B"
    assert _lletra_del_grup("Fase Final") == "Fase Final"


def test_minuts_a_decimal():
    from almeda_pbp.feb.boxscore import _minuts_a_decimal

    assert _minuts_a_decimal("24:57") == pytest.approx(24.95, abs=0.01)
    assert _minuts_a_decimal("40:00") == 40.0
    # Una jugadora que no ha jugat ha de valer 0 minuts, no NaN: si no, tota
    # divisió per minuts es propaga com a NaN.
    assert _minuts_a_decimal("") == 0.0
    assert _minuts_a_decimal("-") == 0.0


def test_desglossa_tirs_gestiona_el_zero():
    from almeda_pbp.feb.boxscore import _desglossa_tirs

    df = pd.DataFrame({"T2": ["4/12", "0/0"], "T3": ["1/3", "0/0"], "TC": ["5/15", "0/0"], "TL": ["2/2", "0/0"]})
    resultat = _desglossa_tirs(df)
    assert resultat.loc[0, "T2C"] == 4 and resultat.loc[0, "T2I"] == 12
    assert resultat.loc[0, "T2 (%)"] == pytest.approx(33.3, abs=0.1)
    assert resultat.loc[1, "T2 (%)"] == 0  # 0/0 no pot donar NaN ni infinit
    assert "T2" not in resultat.columns


def test_magatzem_es_idempotent(tmp_path):
    """Tornar a desar el mateix partit no ha de duplicar files."""
    from almeda_pbp import magatzem

    ruta = tmp_path / "prova.sqlite"
    df = pd.DataFrame(
        {"Temporada": ["2025-26"] * 2, "Lliga": ["A"] * 2, "Jornada": [1, 1],
         "PartitID": [111, 111], "Equip": ["X", "Y"], "Jugador": ["TOTAL", "TOTAL"], "PT": [70, 60]}
    )
    assert magatzem.desa_boxscore(df, ruta) == 2
    magatzem.desa_boxscore(df, ruta)
    assert len(magatzem.carrega_boxscore(ruta)) == 2

    # Un partit diferent s'afegeix sense tocar l'anterior.
    altre = df.assign(PartitID=222)
    magatzem.desa_boxscore(altre, ruta)
    assert len(magatzem.carrega_boxscore(ruta)) == 4
    assert magatzem.partits_desats(ruta) == {111, 222}


def test_magatzem_inexistent_retorna_buit(tmp_path):
    from almeda_pbp import magatzem

    assert magatzem.carrega_boxscore(tmp_path / "no_existeix.sqlite").empty
    assert magatzem.partits_desats(tmp_path / "no_existeix.sqlite") == set()


def test_boxscore_desat_es_coherent():
    """Comprovacions sobre les dades realment scrapejades, si n'hi ha."""
    from almeda_pbp import magatzem

    dades = magatzem.carrega_boxscore()
    if dades.empty:
        pytest.skip("Encara no s'ha executat l'scraper")

    totals = dades[dades["Jugador"] == "TOTAL"]
    # El total de l'acta ha de coincidir amb el marcador del partit.
    assert (totals["PT"] == totals["PT equip"]).all()
    # Cada partit té exactament dos equips i un sol guanyador.
    assert (totals.groupby("PartitID")["Equip"].nunique() == 2).all()
    assert (totals.groupby("PartitID")["Victòria"].sum() == 1).all()
    # La columna Lliga només pot ser A o B.
    assert set(dades["Lliga"].unique()) <= {"A", "B"}


# --- Mètriques de lliga ---------------------------------------------------

def _boxscore_fals():
    """Un partit entre X i Y, només amb les files TOTAL."""
    comu = dict(Temporada="2025-26", Lliga="A", Jornada=1, PartitID=1, Jugador="TOTAL")
    columnes = {c: 0 for c in ["T2C", "T2I", "T3C", "T3I", "TCC", "TCI", "TLC", "TLI",
                               "RO", "RD", "RT", "AS", "BR", "BP", "TapF", "TapC", "MT", "FC", "FR", "VA"]}
    x = {**comu, **columnes, "Equip": "X", "PT": 80, "PT rival": 60,
         "TCC": 30, "TCI": 60, "T3C": 10, "T3I": 20, "T2C": 20, "T2I": 40,
         "TLC": 10, "TLI": 12, "RO": 10, "RD": 30, "BP": 12}
    y = {**comu, **columnes, "Equip": "Y", "PT": 60, "PT rival": 80,
         "TCC": 25, "TCI": 65, "T3C": 5, "T3I": 18, "T2C": 20, "T2I": 47,
         "TLC": 5, "TLI": 8, "RO": 8, "RD": 25, "BP": 15}
    return pd.DataFrame([x, y])


def test_percentatges_es_calculen_sobre_totals():
    """
    Dos partits: 1/1 i 3/20. La resposta correcta és 4/21 = 19%, no la mitjana
    dels percentatges (100% i 15% -> 57,5%).
    """
    from almeda_pbp import lliga

    base = _boxscore_fals()
    p1 = base.copy()
    p1.loc[p1["Equip"] == "X", ["T3C", "T3I"]] = [1, 1]
    p2 = base.copy()
    p2["PartitID"] = 2
    p2["Jornada"] = 2
    p2.loc[p2["Equip"] == "X", ["T3C", "T3I"]] = [3, 20]

    taula = lliga.taula_equips(pd.concat([p1, p2], ignore_index=True))
    valor = taula.loc[taula["Equip"] == "X", "T3 %"].iloc[0]
    assert valor == pytest.approx(19.0, abs=0.1)
    assert valor != pytest.approx(57.5, abs=0.1)


def test_rebot_percentual_usa_les_dades_del_rival():
    """ORB% de X = RO de X / (RO de X + RD de Y)."""
    from almeda_pbp import lliga

    taula = lliga.taula_equips(_boxscore_fals())
    orb_x = taula.loc[taula["Equip"] == "X", "ORB %"].iloc[0]
    assert orb_x == pytest.approx(100 * 10 / (10 + 25), abs=0.1)
    drb_x = taula.loc[taula["Equip"] == "X", "DRB %"].iloc[0]
    assert drb_x == pytest.approx(100 * 30 / (30 + 8), abs=0.1)


def test_direccio_de_les_metriques():
    """Les pèrdues i els punts encaixats han de ser 'com més alt, pitjor'."""
    from almeda_pbp import lliga

    assert lliga.DIRECCIO["BP"] == -1
    assert lliga.DIRECCIO["PT rival"] == -1
    assert lliga.DIRECCIO["DER"] == -1
    assert lliga.DIRECCIO["PT"] == 1
    # El volum de tirs no és ni bo ni dolent: ha de ser neutre perquè no es pinti.
    assert lliga.DIRECCIO["TCI"] == 0


def test_comparativa_ordena_segons_la_direccio():
    from almeda_pbp import lliga

    taula = lliga.taula_equips(_boxscore_fals())
    comp = lliga.comparativa(taula, "X").set_index("Mètrica")
    # X anota més: ha de ser 1r en PT.
    assert comp.loc["PT", "Posició"] == 1
    # X perd MENYS pilotes (12 contra 15): en una mètrica invertida ha de ser 1r.
    assert comp.loc["BP", "Posició"] == 1
    # Les mètriques de volum no tenen rànquing: han de quedar buides.
    assert pd.isna(comp.loc["TCI", "Posició"])


def test_lliga_amb_dades_buides_no_peta():
    from almeda_pbp import lliga

    buit = pd.DataFrame()
    assert lliga.taula_equips(buit).empty
    assert lliga.mitjana_lliga(pd.DataFrame()).empty
    assert lliga.comparativa(pd.DataFrame(), "X").empty


def test_formata_afegeix_el_percentatge():
    from almeda_pbp import lliga

    assert lliga.formata("eFG %", 41.234) == "41.2%"
    assert lliga.formata("PT", 64.29) == "64.3"
    assert lliga.formata("RTL", 0.3333) == "0.333"


# --- Filtres --------------------------------------------------------------

def test_filtre_a_pista_i_protagonista_son_diferents(dades):
    df = dades.dades
    jugadora = df[cfg.COL_FINALITZADORA].dropna().iloc[0]
    a_pista = filtra(df, jugadores=[jugadora], mode_jugadora="a pista")
    protagonista = filtra(df, jugadores=[jugadora], mode_jugadora="protagonista")
    assert len(protagonista) <= len(a_pista)


def test_filtre_buit_no_peta(dades):
    buit = filtra(dades.dades, jornades=[99999])
    assert buit.empty
    assert m.resum_sistemes(buit).empty
    assert m.plus_minus_parelles(buit).empty
    assert m.resum_general(buit)["jugades"] == 0


# --- Temporades (PBP <-> FEB) ----------------------------------------------

def test_conversio_temporada_pbp_feb():
    assert cfg.pbp_a_feb("25-26") == "2025-26"
    assert cfg.feb_a_pbp("2025-26") == "25-26"
    # Ha de fer volta completa per a totes les temporades conegudes.
    for t in cfg.TEMPORADES:
        assert cfg.feb_a_pbp(cfg.pbp_a_feb(t["pbp"])) == t["pbp"]


def test_conversio_temporada_desconeguda_retorna_none():
    assert cfg.pbp_a_feb("99-00") is None
    assert cfg.feb_a_pbp("2099-00") is None


# --- Developer: scraper puntual ---------------------------------------------

def test_assegura_aliases_crea_json_buit(tmp_path):
    from almeda_pbp import dev_scraper

    ruta = tmp_path / "aliases.json"
    assert dev_scraper.assegura_aliases(ruta) is True
    assert ruta.exists()
    assert dev_scraper.llegeix_aliases(ruta) == {}
    # Idempotent: un segon cop no la torna a crear ni la sobreescriu.
    ruta.write_text('{"X": "Y"}', encoding="utf-8")
    assert dev_scraper.assegura_aliases(ruta) is False
    assert dev_scraper.llegeix_aliases(ruta) == {"X": "Y"}


def test_llegeix_aliases_json_invalid_no_peta(tmp_path):
    from almeda_pbp import dev_scraper

    ruta = tmp_path / "aliases.json"
    ruta.write_text("això no és JSON", encoding="utf-8")
    assert dev_scraper.llegeix_aliases(ruta) == {}
    assert dev_scraper.llegeix_aliases(tmp_path / "no_existeix.json") == {}


def test_genera_pbp_construeix_l_ordre_correcta(tmp_path, monkeypatch):
    """
    No es crida Playwright de debò (no hi ha navegador en aquest entorn de
    test): es verifica que `genera_pbp` construeix l'ordre esperada i sap
    interpretar tant l'èxit com el fracàs del subprocess.
    """
    import subprocess as sp

    from almeda_pbp import dev_scraper

    sortida = tmp_path / "j99-pbp-dev.xlsx"
    ordres_capturades = []

    def fals_run(ordre, **kwargs):
        ordres_capturades.append(ordre)
        sortida.write_bytes(b"contingut fals")  # simula que l'script ha escrit l'Excel
        return sp.CompletedProcess(ordre, returncode=0, stdout="Excel creat\n", stderr="")

    monkeypatch.setattr(sp, "run", fals_run)

    resultat = dev_scraper.genera_pbp(
        url="https://baloncestoenvivo.feb.es/partido/1234567",
        jornada=4,
        aliases=tmp_path / "aliases.json",
        sortida=sortida,
        equip="BASKET ALMEDA",
    )

    assert resultat.ok is True
    assert resultat.fitxer == sortida
    ordre = ordres_capturades[0]
    assert "--jornada" in ordre and "4" in ordre
    assert "--team" in ordre and "BASKET ALMEDA" in ordre
    assert "--output" in ordre and str(sortida) in ordre
    assert str(dev_scraper.SCRIPT) in ordre


def test_genera_pbp_marcador_descuadrat_no_crea_fitxer(tmp_path, monkeypatch):
    """Si l'script s'atura (marcador no quadra), no hi ha Excel: ok ha de ser False."""
    import subprocess as sp

    from almeda_pbp import dev_scraper

    def fals_run(ordre, **kwargs):
        return sp.CompletedProcess(ordre, returncode=1, stdout="", stderr="El marcador no coincideix.")

    monkeypatch.setattr(sp, "run", fals_run)

    resultat = dev_scraper.genera_pbp(
        url="https://baloncestoenvivo.feb.es/partido/1234567",
        jornada=4,
        aliases=tmp_path / "aliases.json",
        sortida=tmp_path / "no_es_creara.xlsx",
    )
    assert resultat.ok is False
    assert resultat.fitxer is None
    assert "no coincideix" in resultat.error_consola


# --- Informe a mida ----------------------------------------------------------

def test_informe_a_mida_genera_un_pdf_valid(dades):
    from almeda_pbp import informe

    sistemes = m.resum_sistemes(dades.dades).head(2)[cfg.COL_TACTICA].tolist()
    contingut = informe.genera_informe_a_mida(
        dades.dades,
        ["donut", "pm_individual", "rebot"],
        sistemes=sistemes,
        context={"temporada": "25-26"},
    )
    assert contingut.startswith(b"%PDF")


def test_informe_a_mida_amb_taula_gran_no_peta(dades):
    """
    Regressió: `pm_parelles_posicio` pot tenir moltes files (fins a 7
    combinacions de posicions x moltes parelles) i la imatge resultant, sense
    límit d'alçada, feia petar reportlab amb un LayoutError.
    """
    from almeda_pbp import informe

    contingut = informe.genera_informe_a_mida(dades.dades, ["pm_parelles_posicio", "pm_posicio"])
    assert contingut.startswith(b"%PDF")


def test_informe_a_mida_sense_blocs_no_peta(dades):
    from almeda_pbp import informe

    contingut = informe.genera_informe_a_mida(dades.dades, [])
    assert contingut.startswith(b"%PDF")


def test_informe_a_mida_bloc_desconegut_s_ignora(dades):
    from almeda_pbp import informe

    # Un id de bloc que no existeix al catàleg no ha de petar, només s'ignora.
    contingut = informe.genera_informe_a_mida(dades.dades, ["aixo_no_existeix", "rebot"])
    assert contingut.startswith(b"%PDF")

# --- Etiquetes per sistema -------------------------------------------------

def _pbp_sintetic():
    from almeda_pbp import config as cfg

    return pd.DataFrame({
        cfg.COL_TEMPORADA: ["25-26"] * 5,
        cfg.COL_JORNADA: [1, 1, 1, 2, 2],
        cfg.COL_TACTICA: ["Pisa", "Pisa", "Fons 21", "Triple", "Go"],
        cfg.COL_DESENLLAC: ["T2C", "T2F", "Pèrdua", "T3C", "T2C"],
        cfg.COL_PF: [2, 0, 0, 3, 2],
        cfg.COL_PC: [0, 2, 2, 0, 0],
    })


def _escriu_toml(arrel, cos: str) -> None:
    from almeda_pbp import etiquetes as etq

    ruta = etq.ruta_fitxer(arrel)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(cos, encoding="utf-8")


def test_carrega_etiquetes_normalitza_i_accepta_una_sola_sense_claudators(tmp_path):
    from almeda_pbp import etiquetes as etq

    _escriu_toml(tmp_path, '[sistemes]\n"Pisa" = ["Banda", " banda "]\n"Triple" = "zona"\n"Go" = []\n')
    mapa = etq.carrega_etiquetes(tmp_path)

    # Duplicades i majúscules es pleguen en una sola etiqueta.
    assert mapa == {"Pisa": ["banda"], "Triple": ["zona"], "Go": []}
    assert etq.etiquetes_disponibles(mapa) == ["banda", "zona"]


def test_carrega_etiquetes_sense_fitxer_o_amb_toml_trencat_no_peta(tmp_path):
    from almeda_pbp import etiquetes as etq

    assert etq.carrega_etiquetes(tmp_path) == {}
    _escriu_toml(tmp_path, "[sistemes\naixo no es toml")
    assert etq.carrega_etiquetes(tmp_path) == {}


def test_filtra_per_etiqueta_es_queda_amb_les_jugades_dels_sistemes_marcats(tmp_path):
    from almeda_pbp import config as cfg, etiquetes as etq

    _escriu_toml(
        tmp_path,
        '[sistemes]\n"Pisa" = ["banda"]\n"Fons 21" = ["fons", "banda"]\n"Triple" = ["zona"]\n"Go" = []\n',
    )
    mapa = etq.carrega_etiquetes(tmp_path)
    dades = _pbp_sintetic()

    # "banda" toca Pisa (2 jugades) i Fons 21 (1).
    assert len(etq.filtra_per_etiqueta(dades, mapa, ["banda"])) == 3
    assert etq.sistemes_amb_etiqueta(mapa, ["banda", "fons"], mode="totes") == ["Fons 21"]
    assert etq.sistemes_amb_etiqueta(mapa, ["banda", "zona"], mode="qualsevol") == ["Fons 21", "Pisa", "Triple"]
    assert len(etq.filtra_per_etiqueta(dades, mapa, ["banda", "fons"], mode="totes")) == 1
    # Una etiqueta que no té ningú deixa el conjunt buit, no el conjunt sencer.
    assert etq.filtra_per_etiqueta(dades, mapa, ["inexistent"]).empty
    # Sense etiquetes seleccionades no es toca res.
    assert len(etq.filtra_per_etiqueta(dades, mapa, [])) == len(dades)
    assert cfg.COL_TACTICA in dades.columns


def test_genera_plantilla_conserva_les_etiquetes_i_els_sistemes_orfes(tmp_path):
    """Regenerar amb un PBP diferent no pot esborrar feina feta."""
    from almeda_pbp import etiquetes as etq

    dades = _pbp_sintetic()
    ruta, total, amb_etiqueta = etq.genera_plantilla(dades, tmp_path)
    assert (total, amb_etiqueta) == (4, 0)
    assert set(etq.carrega_etiquetes(tmp_path)) == {"Pisa", "Fons 21", "Triple", "Go"}

    # L'analista etiqueta dos sistemes.
    _escriu_toml(
        tmp_path,
        '[sistemes]\n"Pisa" = ["banda"]\n"Fons 21" = ["fons"]\n"Triple" = []\n"Go" = []\n',
    )

    # Es regenera amb un PBP on ja no hi ha "Fons 21".
    ruta, total, amb_etiqueta = etq.genera_plantilla(dades[dades["Tàctica"] != "Fons 21"], tmp_path)
    mapa = etq.carrega_etiquetes(tmp_path)
    assert mapa["Pisa"] == ["banda"]
    # L'orfe amb etiquetes es conserva; podria ser d'una temporada no carregada.
    assert mapa["Fons 21"] == ["fons"]
    assert (total, amb_etiqueta) == (4, 2)


def test_genera_plantilla_ordena_per_us_i_escriu_el_comptatge(tmp_path):
    from almeda_pbp import etiquetes as etq

    ruta, _, _ = etq.genera_plantilla(_pbp_sintetic(), tmp_path)
    linies = [l for l in ruta.read_text(encoding="utf-8").splitlines() if l.startswith('"')]

    assert linies[0].startswith('"Pisa"'), "El sistema més jugat va primer."
    assert "# 2 jugades" in linies[0]


# --- Plantilla des de l'acta oficial ---------------------------------------

def _boxscore_sintetic():
    """Dos partits de dues jugadores, amb la fila TOTAL que s'ha d'ignorar."""
    files = [
        # Jornada 1: A fa 1/1 de 2; B fa 0/1.
        dict(Jornada=1, Jugador="TIERNO MARTÍ, LAURA", Dorsal=7, Inicial=1, MIN=20.0, PT=2, T2C=1, T2I=1, T3C=0, T3I=0, TCC=1, TCI=1, TLC=0, TLI=0, RO=1, RD=2, RT=3, AS=2, BR=0, BP=1, TapF=0, TapC=0, MT=0, FC=2, FR=1, VA=5),
        dict(Jornada=1, Jugador="PUJOL MARTINEZ, CRISTINA", Dorsal=9, Inicial=0, MIN=10.0, PT=0, T2C=0, T2I=1, T3C=0, T3I=0, TCC=0, TCI=1, TLC=0, TLI=0, RO=0, RD=1, RT=1, AS=0, BR=1, BP=0, TapF=0, TapC=0, MT=0, FC=1, FR=0, VA=1),
        dict(Jornada=1, Jugador="TOTAL", Dorsal=0, Inicial=0, MIN=200.0, PT=2, T2C=1, T2I=2, T3C=0, T3I=0, TCC=1, TCI=2, TLC=0, TLI=0, RO=1, RD=3, RT=4, AS=2, BR=1, BP=1, TapF=0, TapC=0, MT=0, FC=3, FR=1, VA=6),
        # Jornada 2: A fa 3/19 de 2. Acumulat 4/20 = 20%, no la mitjana de 100% i 15.8%.
        dict(Jornada=2, Jugador="TIERNO MARTÍ, LAURA", Dorsal=7, Inicial=1, MIN=30.0, PT=6, T2C=3, T2I=19, T3C=0, T3I=0, TCC=3, TCI=19, TLC=0, TLI=0, RO=1, RD=1, RT=2, AS=4, BR=2, BP=3, TapF=1, TapC=0, MT=0, FC=0, FR=2, VA=7),
    ]
    base = dict(Temporada="2025-26", Lliga="A", Equip="BASKET ALMEDA", Rival="X", Pista="Casa")
    return pd.DataFrame([{**base, **f, "PartitID": f["Jornada"]} for f in files])


def test_plantilla_oficial_ignora_el_total_i_acumula_els_percentatges(tmp_path):
    from almeda_pbp import jugadores as jug

    taula = jug.plantilla_oficial(_boxscore_sintetic(), "2025-26", arrel=tmp_path)

    assert len(taula) == 2, "La fila TOTAL no és cap jugadora."
    tierno = taula[taula["Nom oficial"] == "TIERNO MARTÍ, LAURA"].iloc[0]
    assert tierno["Partits"] == 2 and tierno["Titular"] == 2
    assert tierno["PT"] == 8 and tierno["MIN"] == 50.0
    # 4/20 acumulat = 20%, no (100% + 15.8%) / 2 = 57.9%.
    assert tierno["T2 (%)"] == 20.0


def test_plantilla_oficial_per_partit_no_toca_els_percentatges(tmp_path):
    from almeda_pbp import jugadores as jug

    boxscore = _boxscore_sintetic()
    totals = jug.plantilla_oficial(boxscore, "2025-26", arrel=tmp_path).set_index("Nom oficial")
    mitjana = jug.plantilla_oficial(boxscore, "2025-26", per_partit=True, arrel=tmp_path).set_index("Nom oficial")

    assert mitjana.loc["TIERNO MARTÍ, LAURA", "PT"] == 4.0
    assert mitjana.loc["TIERNO MARTÍ, LAURA", "T2 (%)"] == totals.loc["TIERNO MARTÍ, LAURA", "T2 (%)"]


def test_plantilla_oficial_filtra_per_jornada_i_temporada(tmp_path):
    from almeda_pbp import jugadores as jug

    boxscore = _boxscore_sintetic()
    nomes_j1 = jug.plantilla_oficial(boxscore, "2025-26", jornades=[1], arrel=tmp_path)
    assert set(nomes_j1["Partits"]) == {1}
    assert jug.plantilla_oficial(boxscore, "2026-27", arrel=tmp_path).empty


def test_genera_noms_no_endevina_les_correspondencies_ambigues(tmp_path):
    """Un nom curt que encaixa amb dues jugadores es deixa buit, no se n'agafa una."""
    from almeda_pbp import jugadores as jug

    boxscore = _boxscore_sintetic()
    # "Mar" és dins de "MARTÍ" i de "MARTINEZ": ambigu.
    ruta, total, resolts = jug.genera_noms(["Tierno", "Mar", "Puyi"], boxscore, arrel=tmp_path)
    mapa = jug.carrega_noms(tmp_path)

    assert (total, resolts) == (3, 1)
    assert mapa == {"Tierno": "TIERNO MARTÍ, LAURA"}
    assert '"Mar" = ""' in ruta.read_text(encoding="utf-8")


def test_genera_noms_conserva_el_que_ja_hi_ha_escrit(tmp_path):
    from almeda_pbp import jugadores as jug

    boxscore = _boxscore_sintetic()
    jug.genera_noms(["Tierno", "Puyi"], boxscore, arrel=tmp_path)

    # L'analista resol a mà el que l'automatisme no podia saber.
    ruta = jug.ruta_fitxer(tmp_path)
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace('"Puyi" = ""', '"Puyi" = "PUJOL MARTINEZ, CRISTINA"'),
        encoding="utf-8",
    )

    _, _, resolts = jug.genera_noms(["Tierno", "Puyi", "Bet"], boxscore, arrel=tmp_path)
    assert resolts == 2
    assert jug.carrega_noms(tmp_path)["Puyi"] == "PUJOL MARTINEZ, CRISTINA"


def test_plantilla_oficial_fa_servir_el_nom_curt_quan_n_hi_ha(tmp_path):
    from almeda_pbp import jugadores as jug

    boxscore = _boxscore_sintetic()
    ruta = jug.ruta_fitxer(tmp_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text('[noms]\n"Tierno" = "TIERNO MARTÍ, LAURA"\n', encoding="utf-8")

    taula = jug.plantilla_oficial(boxscore, "2025-26", arrel=tmp_path).set_index("Nom oficial")
    assert taula.loc["TIERNO MARTÍ, LAURA", "Jugadora"] == "Tierno"
    # Sense correspondència es fa servir el nom oficial, no es perd la jugadora.
    assert taula.loc["PUJOL MARTINEZ, CRISTINA", "Jugadora"] == "PUJOL MARTINEZ, CRISTINA"


# --- Rebot -----------------------------------------------------------------

def _pbp_rebot():
    from almeda_pbp import config as cfg

    return pd.DataFrame({
        cfg.COL_PERIODE: [1, 1, 2, 5],
        cfg.COL_TACTICA: ["Go", "RO", "RO", "Go"],
        cfg.COL_DESENLLAC: ["T2F", "T2C", "Pèrdua", "T3C"],
        cfg.COL_PF: [0, 2, 0, 3],
        cfg.COL_PC: [0, 0, 2, 0],
        "jug 1": ["A", "A", "B", "A"],
        "jug 2": ["B", "B", "C", "B"],
        "jug 3": [None, None, None, None],
        "jug 4": [None, None, None, None],
        "jug 5": [None, None, None, None],
        "RO a favor": [1, 0, 2, 1],
        "RO en contra": [2, 1, 0, 0],
        "Punts RO a favor": [0, 2, 0, 3],
        "Punts RO rival": [2, 0, 0, 0],
    })


def test_eficiencia_ro_compara_amb_el_sostre_de_dos_punts():
    df = _pbp_rebot()
    resultat = m.eficiencia_ro(df)

    assert resultat["ro"] == 4 and resultat["punts"] == 5
    assert resultat["potencial"] == 4 * m.PUNTS_PER_RO == 8
    assert resultat["aprofitament"] == pytest.approx(62.5)
    assert resultat["punts_per_ro"] == pytest.approx(1.25)
    assert resultat["ro_rival"] == 3 and resultat["punts_rival"] == 2


def test_eficiencia_ro_amb_zero_rebots_no_divideix_per_zero():
    df = _pbp_rebot()
    df[["RO a favor", "Punts RO a favor"]] = 0
    resultat = m.eficiencia_ro(df)
    assert resultat["aprofitament"] == 0.0 and resultat["punts_per_ro"] == 0.0


def test_potencial_ro_afegeix_el_sostre_a_la_taula_per_periode():
    taula = m.potencial_ro(m.resum_rebot_ofensiu(_pbp_rebot()))
    assert (taula["Potencial RO a favor"] == taula["RO a favor"] * m.PUNTS_PER_RO).all()
    assert (taula["Potencial RO rival"] == taula["RO en contra"] * m.PUNTS_PER_RO).all()


def test_despres_de_rebot_nomes_agafa_les_files_de_continuacio():
    taula = m.despres_de_rebot(_pbp_rebot())
    assert set(taula["Desenllac"]) == {"T2C", "Pèrdua"}, "Només les files amb Tàctica == RO."
    assert int(taula["Jugades"].sum()) == 2
    assert taula["% de les jugades"].sum() == pytest.approx(100.0)


def test_rebots_per_jugadora_en_pista_normalitza_per_jugades():
    taula = m.rebots_per_jugadora_en_pista(_pbp_rebot(), columna="RO en contra").set_index("Jugadora")

    # A és a pista a les files 0, 1 i 3: 2 + 1 + 0 = 3 en contra en 3 jugades.
    assert taula.loc["A", "RO en contra"] == 3 and taula.loc["A", "Jugades"] == 3
    assert taula.loc["A", "RO en contra per 100 jugades"] == pytest.approx(100.0)
    # C només és a la fila 2, amb 0 en contra.
    assert taula.loc["C", "RO en contra"] == 0 and taula.loc["C", "Jugades"] == 1


def test_rebots_per_jugadora_en_pista_sense_la_columna_retorna_buit():
    df = _pbp_rebot().drop(columns=["RO en contra"])
    assert m.rebots_per_jugadora_en_pista(df, columna="RO en contra").empty


def test_resum_rebot_calcula_orb_i_drb_sobre_els_disponibles():
    """ORB% propi i DRB% del rival han de sumar 100: tot rebot se l'endú algú."""
    from almeda_pbp import lliga

    def _total(partit, equip, ro, rd):
        return dict(
            Temporada="2025-26", Lliga="A", Jornada=partit, PartitID=partit, Equip=equip,
            Jugador="TOTAL", RO=ro, RD=rd, TCI=50, TLI=10, BP=10, PT=60,
        )

    boxscore = pd.DataFrame([
        _total(1, "BASKET ALMEDA", 10, 20),
        _total(1, "RIVAL", 5, 30),
        _total(2, "BASKET ALMEDA", 6, 24),
        _total(2, "RIVAL", 9, 14),
    ])

    resultat = lliga.resum_rebot(boxscore, "2025-26", "BASKET ALMEDA")

    assert resultat["partits"] == 2
    assert resultat["ro"] == 16 and resultat["rd"] == 44
    assert resultat["ro_rival"] == 14 and resultat["rd_rival"] == 44
    # 16 propis sobre 16 + 44 defensius del rival = 26.7%.
    assert resultat["orb"] == pytest.approx(26.7, abs=0.1)
    assert resultat["orb"] + resultat["drb_rival"] == pytest.approx(100.0, abs=0.1)
    assert resultat["drb"] + resultat["orb_rival"] == pytest.approx(100.0, abs=0.1)


def test_resum_rebot_sense_actes_retorna_zeros_i_no_peta():
    from almeda_pbp import lliga

    buit = lliga.resum_rebot(pd.DataFrame(), "2025-26", "BASKET ALMEDA")
    assert buit["partits"] == 0 and buit["orb"] == 0.0
