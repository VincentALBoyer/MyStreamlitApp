import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import unicodedata

# Define the puzzles in a modular structure (v3)
PUZZLES = [
    {
        "id": 1,
        "title": "Room 1: El Almacén de Suministros",
        "type": "text",
        "clue": "Busca la fórmula de 'Tamaño de lote económico' (EOQ).",
        "task": "¿Qué variable representa el 'Costo de preparación'?",
        "answer": "S",
        "hint": "Consulta la página 26."
    },
    {
        "id": 2,
        "title": "Room 2: El Laboratorio de Pronósticos",
        "type": "numeric",
        "clue": "Localiza las secciones de 'Suavizamiento exponencial doble' y 'MAPE'.",
        "task": "Suma los números de página donde aparecen estos dos conceptos.",
        "answer": "51",
        "hint": "Pág 25 + Pág 26 = 51."
    },
    {
        "id": 3,
        "title": "Room 3: El Centro Logístico",
        "type": "choice",
        "clue": "Revisa la sección de 'Centro de gravedad'.",
        "task": "¿Qué representa la variable 'w_i'?",
        "choices": [
            "peso de la unidad",
            "ponderación del indicador",
            "ancho de la vía",
            "valor del inventario"
        ],
        "answer": "ponderación del indicador",
        "hint": "Mira la sección 'donde:' en la página 28."
    },
    {
        "id": 4,
        "title": "Room 4: La Sala de Control de Métricas",
        "type": "choice",
        "clue": "Encuentra la métrica '% Precisión de entrega'.",
        "task": "¿Cuál es el texto exacto del denominador en la fórmula?",
        "choices": [
            "Valor del producto que se envió al cliente",
            "Valor del producto ordenado",
            "Ventas netas totales",
            "Gastos de operación"
        ],
        "answer": "Valor del producto que se envió al cliente",
        "hint": "Revisa la página 28."
    },
    {
        "id": 5,
        "title": "Room 5: Cálculo de Lote Económico",
        "type": "numeric",
        "clue": "Usa la fórmula de Q* (EOQ).",
        "task": "Si la demanda anual (D) es 2000, el costo de preparación (S) es 100 y el costo de mantener (H) es 10, ¿cuál es el lote económico (Q*)?",
        "answer": "200",
        "hint": "Q* = √((2 * 2000 * 100) / 10) = √40000. Página 26."
    },
    {
        "id": 6,
        "title": "Room 6: El Radar de Rastreo",
        "type": "text",
        "clue": "Busca la fórmula de 'Señal de rastreo'.",
        "task": "¿Qué sigla aparece en el denominador de esta fórmula?",
        "answer": "DAM",
        "hint": "Página 25. Significa Desviación Absoluta Media."
    },
    {
        "id": 7,
        "title": "Room 7: Inventarios de Calidad",
        "type": "choice",
        "clue": "Revisa la sección de 'Inventarios'.",
        "task": "¿Qué significa la sigla 'RIANSC'?",
        "choices": [
            "Rotación de inventario acumulada no solicitada",
            "Rendimiento inicial de activos no servidos",
            "Rotación del inventario ajustado al nivel del servicio del cliente",
            "Relación de inventario anual sobre costos"
        ],
        "answer": "Rotación del inventario ajustado al nivel del servicio del cliente",
        "hint": "Página 29."
    },
    {
        "id": 8,
        "title": "Room 8: El Cuello de Botella",
        "type": "choice",
        "clue": "Localiza 'Planeación de recursos'.",
        "task": "¿Cuál es el denominador en la fórmula de 'Producción máxima'?",
        "choices": [
            "Tiempo de trabajo",
            "Tiempo promedio de llegada",
            "Tiempo del cuello de botella",
            "Demanda del cliente"
        ],
        "answer": "Tiempo del cuello de botella",
        "hint": "Página 28."
    },
    {
        "id": 9,
        "title": "Room 9: Efectividad de Ventas",
        "type": "numeric",
        "clue": "Busca la fórmula del Índice de Efectividad de Ventas (IEV).",
        "task": "¿Cuántos componentes se multiplican para obtener el IEV?",
        "answer": "3",
        "hint": "Mira la fórmula en la página 30."
    },
    {
        "id": 10,
        "title": "Room 10: El Coeficiente Maestro",
        "type": "numeric",
        "clue": "Estudia la fórmula del 'Coeficiente de correlación'.",
        "task": "Cuenta el número total de veces que aparece el símbolo de sumatoria (Σ) en toda la expresión de 'r'.",
        "answer": "7",
        "hint": "Página 25. 3 en el numerador y 4 en el denominador (bajo la raíz)."
    }
]

FINAL_KEYWORD = "LOGISTICA"

class GameLogic:
    def __init__(self, platform="colab"):
        self.current_room = 0
        self.platform = platform
        self.completed = False
        self.hints_used = 0
        self.room_hint_used = False

    def normalize(self, s):
        if not isinstance(s, str):
            s = str(s)
        s = s.lower().strip()
        return "".join(c for c in unicodedata.normalize('NFD', s)
                      if unicodedata.category(c) != 'Mn')

    def check_answer(self, user_answer):
        puzzle = PUZZLES[self.current_room]
        
        if self.normalize(user_answer) == self.normalize(puzzle['answer']):
            self.current_room += 1
            self.room_hint_used = False
            if self.current_room >= len(PUZZLES):
                self.completed = True
            return True, "¡Correcto! Has avanzado de nivel."
        else:
            return False, f"Incorrecto. Intenta de nuevo. Revisa tu formulario."

    def use_hint(self):
        if not self.room_hint_used:
            self.hints_used += 1
            self.room_hint_used = True
        return PUZZLES[self.current_room]['hint']

    def get_progress(self):
        return (self.current_room / len(PUZZLES)) * 100

    def get_rank(self):
        if self.hints_used == 0: return "Maestro de Suministros (0 pistas)"
        if self.hints_used <= 3: return "Experto Logístico (1-3 pistas)"
        if self.hints_used <= 6: return "Analista Jr. (4-6 pistas)"
        return "Estudiante de Repaso (7+ pistas)"

# Colab UI Implementation
class ColabGame:
    def __init__(self):
        self.logic = GameLogic(platform="colab")
        self.output = widgets.Output()
        
    def start(self):
        self.render()

    def render(self):
        with self.output:
            clear_output()
            if self.logic.completed:
                display(HTML(f"""
                    <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; border: 1px solid #c3e6cb;">
                        <h2 style="color: #155724;">🎉 ¡FELICIDADES! 🎉</h2>
                        <p>Has escapado con éxito. Rango: <b>{self.logic.get_rank()}</b></p>
                        <p>Pistas totales: <b>{self.logic.hints_used}</b></p>
                        <p style="font-size: 20px; font-weight: bold;">PALABRA CLAVE FINAL: <span style="color: #721c24;">{FINAL_KEYWORD}</span></p>
                    </div>
                """))
                return

            puzzle = PUZZLES[self.logic.current_room]
            
            # Progress bar
            progress = widgets.FloatProgress(
                value=self.logic.get_progress(), min=0, max=100,
                description='Progreso:', bar_style='info'
            )
            
            display(HTML(f"<h3>{puzzle['title']}</h3>"))
            display(HTML(f"<p><b>🔍 Contexto:</b> {puzzle['clue']}</p>"))
            display(HTML(f"<p><b>🎯 Reto:</b> {puzzle['task']}</p>"))
            
            # Input based on type
            if puzzle['type'] == 'choice':
                ans_input = widgets.Dropdown(options=["-- Selecciona --"] + puzzle['choices'])
            else:
                ans_input = widgets.Text(placeholder='Respuesta...')
                
            btn_valid = widgets.Button(description="Validar", button_style='success')
            btn_hint = widgets.Button(description="⚠️ Ver Pista", button_style='warning')
            feedback = widgets.Label(value="")
            hint_label = widgets.Label(value="")

            def on_valid(b):
                correct, msg = self.logic.check_answer(ans_input.value)
                feedback.value = msg
                if correct:
                    self.render()

            def on_hint(b):
                hint_label.value = f"Pista: {self.logic.use_hint()}"

            btn_valid.on_click(on_valid)
            btn_hint.on_click(on_hint)
            
            display(progress, ans_input, widgets.HBox([btn_valid, btn_hint]), feedback, hint_label)
            
        display(self.output)
