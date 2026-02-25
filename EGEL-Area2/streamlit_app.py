import streamlit as st
from game_utils import PUZZLES, FINAL_KEYWORD, GameLogic

# Page Config
st.set_page_config(page_title="SCM Escape Room v3", page_icon="🔒", layout="centered")

# CSS
st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .room-card {
        background: white; padding: 1.5em; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 1.5em;
        border-left: 5px solid #4CAF50;
    }
    .hint-text { color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'game_logic' not in st.session_state:
    st.session_state.game_logic = GameLogic(platform="streamlit")

logic = st.session_state.game_logic

st.title("🔐 Supply Chain Escape Room")
st.caption("EGEL Plus IINDU - Verificación de Formulario")

if logic.completed:
    st.balloons()
    st.success("## 🏆 ESCAPE COMPLETADO")
    st.write(f"Tu rango: **{logic.get_rank()}**")
    st.write(f"Pistas utilizadas: **{logic.hints_used}**")
    st.markdown(f"<div style='text-align:center; padding:20px; background:#f8f9fa; border:2px dashed #4CAF50; border-radius:10px;'><h3>🔑 CLAVE FINAL: {FINAL_KEYWORD}</h3></div>", unsafe_allow_html=True)
    if st.button("Reintentar (Reset)"):
        st.session_state.game_logic = GameLogic(platform="streamlit")
        st.rerun()
else:
    # Sidebar stats
    st.sidebar.metric("Nivel", f"{logic.current_room + 1} / {len(PUZZLES)}")
    st.sidebar.metric("Pistas Usadas", logic.hints_used)
    
    st.progress(logic.get_progress()/100)
    
    puzzle = PUZZLES[logic.current_room]
    
    with st.container():
        st.markdown(f"""
            <div class="room-card">
                <h3>{puzzle['title']}</h3>
                <p><b>🔍 Contexto:</b> {puzzle['clue']}</p>
                <hr>
                <p><b>🎯 Tarea:</b> {puzzle['task']}</p>
            </div>
        """, unsafe_allow_html=True)

        if puzzle['type'] == 'choice':
            user_ans = st.selectbox("Selecciona la opción correcta:", ["-- Elige una --"] + puzzle['choices'], key=f"sel_{logic.current_room}")
        elif puzzle['type'] == 'numeric':
            user_ans = st.text_input("Ingresa un número:", key=f"num_{logic.current_room}")
        else:
            user_ans = st.text_input("Ingresa tu respuesta:", key=f"txt_{logic.current_room}")

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Validar Respuesta", type="primary"):
                if user_ans and user_ans != "-- Elige una --":
                    correct, msg = logic.check_answer(user_ans)
                    if correct:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Debes ingresar una respuesta.")
        
        with col2:
            if st.button("💡 Ver Pista"):
                st.session_state.show_hint = True
        
        if st.session_state.get('show_hint', False):
            hint = logic.use_hint()
            st.markdown(f"<div class='hint-text'><b>Pista:</b> {hint}</div>", unsafe_allow_html=True)
            # Reset hint visibility on next run unless button clicked again
            st.session_state.show_hint = False

st.sidebar.info("Usa tu PDF oficial (Páginas 24-30) para encontrar las respuestas. ¡Buena suerte!")
