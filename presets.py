import streamlit as st


def apply_preset_to_session(name):

    if name == "Arquitectura estable":

        preset_values = {
            "P1": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P2": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P3": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P4": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P5": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P6": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P7": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P8": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P9": (7.2,7.2,7.2,7.2,7.2,7.2),
            "P10": (7.2,7.2,7.2,7.2,7.2,7.2),
        }

    elif name == "Potencia con fuga estructural":

        preset_values = {
            "P1": (6.8,8.2,4.1,6.9,7.4,5.0),
            "P2": (7.0,8.5,4.2,6.7,8.0,4.8),
            "P3": (7.4,8.8,3.9,7.1,8.4,4.6),
            "P4": (6.9,8.1,4.3,6.5,8.2,4.9),
            "P5": (5.9,6.6,3.8,5.8,6.4,4.2),
            "P6": (7.1,7.8,4.5,7.4,7.0,4.8),
            "P7": (6.0,6.9,3.9,6.1,6.2,4.6),
            "P8": (6.7,7.9,4.4,6.9,7.3,5.0),
            "P9": (6.5,7.3,4.6,7.0,6.5,4.9),
            "P10": (6.4,7.2,4.1,6.2,6.9,5.1),
        }

    elif name == "Sistema en riesgo crítico":

        preset_values = {
            "P1":  (2.2, 3.4, 0.8, 2.1, 2.9, 1.0),
            "P2":  (2.0, 3.8, 0.7, 1.9, 3.1, 0.9),
            "P3":  (1.8, 3.6, 0.5, 1.7, 2.8, 0.7),
            "P4":  (2.1, 3.2, 0.9, 1.8, 3.0, 0.8),
            "P5":  (1.6, 2.6, 0.4, 1.4, 2.2, 0.5),
            "P6":  (2.4, 3.1, 0.8, 2.0, 2.7, 0.9),
            "P7":  (1.5, 2.4, 0.3, 1.3, 2.0, 0.4),
            "P8":  (1.7, 3.0, 0.5, 1.5, 2.4, 0.6),
            "P9":  (2.3, 3.3, 0.7, 2.1, 2.5, 0.8),
            "P10": (1.9, 2.8, 0.5, 1.6, 2.3, 0.6),
        }

    else:
        return

    for p_code, vals in preset_values.items():

        m1, m2, m3, r, c, a = vals

        st.session_state[f"{p_code}_m1"] = m1
        st.session_state[f"{p_code}_m2"] = m2
        st.session_state[f"{p_code}_m3"] = m3

        st.session_state[f"{p_code}_r"] = r
        st.session_state[f"{p_code}_c"] = c
        st.session_state[f"{p_code}_a"] = a


def get_preset_narrative(name):

    if name == "Arquitectura estable":
        return {
            "titulo": "Caso demo: arquitectura estable",
            "descripcion": "Organización con coherencia interna, estructura suficiente y baja fricción relativa.",
            "lectura": "Este caso muestra un sistema donde la potencia está bien distribuida y la arquitectura sostiene el mando.",
            "mirar": "Observa la baja fricción y la coherencia del sistema.",
            "intervencion": "La intervención aquí consiste en preservar la arquitectura y evitar degradación."
        }

    elif name == "Potencia con fuga estructural":
        return {
            "titulo": "Caso demo: potencia con fuga estructural",
            "descripcion": "Sistema con energía, actividad y presión estratégica pero con estructura insuficiente.",
            "lectura": "La organización parece fuerte pero pierde eficiencia por desalineación estructural.",
            "mirar": "Observa potencia relativamente alta combinada con fricción significativa.",
            "intervencion": "Refuerzo de estructura y autoridad en los poderes más fugados."
        }

    elif name == "Sistema en riesgo crítico":
        return {
            "titulo": "Caso demo: sistema en riesgo crítico",
            "descripcion": "Arquitectura debilitada con estructura y legitimidad insuficientes.",
            "lectura": "La organización ya no sufre un problema local sino sistémico.",
            "mirar": "Observa acumulación de fragilidad y fricción elevada.",
            "intervencion": "Reforzar estructura, autoridad y base operativa en múltiples frentes."
        }

    else:
        return None


