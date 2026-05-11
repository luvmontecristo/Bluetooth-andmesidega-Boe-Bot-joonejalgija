import random
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QFont, QColor

WORDS = [
    "the", "of", "to", "and", "a", "in", "is", "it", "you", "that", "he", "was", "for", "on", "are", 
    "with", "as", "I", "his", "they", "be", "at", "one", "have", "this", "from", "or", "had", "by", 
    "not", "word", "but", "what", "some", "we", "can", "out", "other", "were", "all", "there", "when", 
    "up", "use", "your", "how", "said", "an", "each", "she", "which", "do", "their", "time", "if", 
    "will", "way", "about", "many", "then", "them", "write", "would", "like", "so", "these", "her", 
    "long", "make", "thing", "see", "him", "two", "has", "look", "more", "day", "could", "go", "come", 
    "did", "number", "sound", "no", "most", "people", "my", "over", "know", "water", "than", "call", 
    "first", "who", "may", "down", "side", "been", "now", "find", "any", "new", "work", "part", "take", 
    "get", "place", "made", "live", "where", "after", "back", "little", "only", "round", "man", "year", 
    "came", "show", "every", "good", "me", "give", "our", "under", "name", "very", "through", "just", 
    "form", "sentence", "great", "think", "say", "help", "low", "line", "differ", "turn", "cause", 
    "much", "mean", "before", "move", "right", "boy", "old", "too", "same", "tell", "does", "set", 
    "three", "want", "air", "well", "also", "play", "small", "end", "put", "home", "read", "hand", 
    "port", "large", "spell", "add", "even", "land", "here", "must", "big", "high", "such", "follow", 
    "act", "why", "ask", "men", "change", "went", "light", "kind", "off", "need", "house", "picture", 
    "try", "us", "again", "animal", "point", "mother", "world", "near", "build", "self", "earth", 
    "father", "head", "stand", "own", "page", "should", "country", "found", "answer", "school", "grow", 
    "study", "still", "learn", "plant", "cover", "food", "sun", "four", "between", "state", "keep", 
    "eye", "never", "last", "let", "thought", "city", "tree", "cross", "farm", "hard", "start", 
    "might", "story", "saw", "far", "sea", "draw", "left", "late", "run", "don't", "while", "press", 
    "close", "night", "real", "life", "few", "north", "open", "seem", "together", "next", "white", 
    "children", "begin", "got", "walk", "example", "ease", "paper", "group", "always", "music", 
    "those", "both", "mark", "often", "letter", "until", "mile", "river", "car", "feet", "care", 
    "second", "book", "carry", "took", "science", "eat", "room", "friend", "began", "idea", "fish", 
    "mountain", "stop", "once", "base", "hear", "horse", "cut", "sure", "watch", "color", "face", 
    "wood", "main", "enough", "plain", "girl", "usual", "young", "ready", "above", "ever", "red", 
    "list", "though", "feel", "talk", "bird", "soon", "body", "dog", "family", "direct", "pose", 
    "leave", "song", "measure", "door", "product", "black", "short", "numeral", "class", "wind", 
    "question", "happen", "complete", "ship", "area", "half", "rock", "order", "fire", "south", 
    "problem", "piece", "told", "knew", "pass", "since", "top", "whole", "king", "space", "heard", 
    "best", "hour", "better", "true", "during", "hundred", "five", "remember", "step", "early", 
    "hold", "west", "ground", "interest", "reach", "fast", "verb", "sing", "listen", "six", "table", 
    "travel", "less", "morning", "ten", "simple", "several", "vowel", "toward", "war", "lay", 
    "against", "pattern", "slow", "center", "love", "person", "money", "serve", "appear", "road", 
    "map", "rain", "rule", "govern", "pull", "cold", "notice", "voice", "unit", "power", "town", 
    "fine", "certain", "fly", "fall", "lead", "cry", "dark", "machine", "note", "wait", "plan", 
    "figure", "star", "box", "noun", "field", "rest", "correct", "able", "pound", "done", "beauty", 
    "drive", "stood", "contain", "front", "teach", "week", "final", "gave", "green", "oh", "quick", 
    "develop", "ocean", "warm", "free", "minute", "strong", "special", "mind", "behind", "clear", 
    "tail", "produce", "fact", "street", "inch", "multiply", "nothing", "course", "stay", "wheel", 
    "full", "force", "blue", "object", "decide", "surface", "deep", "moon", "island", "foot", "system", 
    "busy", "test", "record", "boat", "common", "gold", "possible", "plane", "stead", "dry", "wonder", 
    "laugh", "thousand", "ago", "ran", "check", "game", "shape", "equate", "hot", "miss", "brought", 
    "heat", "snow", "tire", "bring", "yes", "distant", "fill", "east", "paint", "language", "among", 
    "grand", "ball", "yet", "wave", "drop", "heart", "am", "present", "heavy", "dance", "engine", 
    "position", "arm", "wide", "sail", "material", "size", "vary", "settle", "speak", "weight", 
    "general", "ice", "matter", "circle", "pair", "include", "divide", "syllable", "felt", "perhaps", 
    "pick", "sudden", "square", "reason", "length", "represent", "art", "subject", "region", "energy", 
    "hunt", "probable", "bed", "brother", "egg", "ride", "cell", "believe", "fraction", "forest", 
    "sit", "race", "window", "store", "summer", "train", "sleep", "prove", "lone", "leg", "exercise", 
    "wall", "catch", "mount", "wish", "sky", "board", "joy", "winter", "sat", "written", "wild", 
    "instrument", "kept", "glass", "grass", "cow", "job", "edge", "sign", "visit", "past", "soft", 
    "fun", "bright", "gas", "weather", "month", "million", "bear", "finish", "happy", "hope", "flower", 
    "clothe", "strange", "gone", "jump", "baby", "eight", "village", "meet", "root", "buy", "raise", 
    "solve", "metal", "whether", "push", "seven", "paragraph", "third", "shall", "held", "hair", 
    "describe", "cook", "floor", "either", "result", "burn", "hill", "safe", "cat", "century", 
    "consider", "type", "law", "bit", "coast", "copy", "phrase", "silent", "tall", "sand", "soil", 
    "roll", "temperature", "finger", "industry", "value", "fight", "lie", "beat", "excite", "natural", 
    "view", "sense", "ear", "else", "quite", "broke", "case", "middle", "kill", "son", "lake", 
    "moment", "scale", "loud", "spring", "observe", "child", "straight", "consonant", "nation", 
    "dictionary", "milk", "speed", "method", "organ", "pay", "age", "section", "dress", "cloud", 
    "surprise", "quiet", "stone", "tiny", "climb", "cool", "design", "poor", "lot", "experiment", 
    "bottom", "key", "iron", "single", "stick", "flat", "twenty", "skin", "smile", "crease", "hole", 
    "trade", "melody", "trip", "office", "receive", "row", "mouth", "exact", "symbol", "die", 
    "least", "trouble", "shout", "except", "wrote", "seed", "tone", "join", "suggest", "clean", 
    "break", "lady", "yard", "rise", "bad", "blow", "oil", "blood", "touch", "grew", "cent", "mix", 
    "team", "wire", "cost", "lost", "brown", "wear", "garden", "equal", "sent", "choose", "fell", 
    "fit", "flow", "fair", "bank", "collect", "save", "control", "decimal", "gentle", "woman", 
    "captain", "practice", "separate", "difficult", "doctor", "please", "protect", "noon", "whose", 
    "locate", "ring", "character", "insect", "caught", "period", "indicate", "radio", "spoke", 
    "atom", "human", "history", "effect", "electric", "expect", "crop", "modern", "element", "hit", 
    "student", "corner", "party", "supply", "bone", "rail", "imagine", "provide", "agree", "thus", 
    "capital", "won't", "chair", "danger", "fruit", "rich", "thick", "soldier", "process", "operate", 
    "guess", "necessary", "sharp", "wing", "create", "neighbor", "wash", "bat", "rather", "crowd", 
    "corn", "compare", "poem", "string", "bell", "depend", "meat", "rub", "tube", "famous", "dollar", 
    "stream", "fear", "sight", "thin", "triangle", "planet", "hurry", "chief", "colony", "clock", 
    "mine", "tie", "enter", "major", "fresh", "search", "send", "yellow", "gun", "allow", "print", 
    "dead", "spot", "desert", "suit", "current", "lift", "rose", "continue", "block", "chart", 
    "hat", "sell", "success", "company", "subtract", "event", "particular", "deal", "swim", "term", 
    "opposite", "wife", "shoe", "shoulder", "spread", "arrange", "camp", "invent", "cotton", 
    "born", "determine", "quart", "nine", "truck", "noise", "level", "chance", "gather", "shop", 
    "stretch", "throw", "shine", "property", "column", "molecule", "select", "wrong", "gray", 
    "repeat", "require", "broad", "prepare", "salt", "nose", "plural", "anger", "claim", "continent", 
    "oxygen", "sugar", "death", "pretty", "skill", "women", "season", "solution", "magnet", "silver", 
    "thank", "branch", "match", "suffix", "especially", "fig", "afraid", "huge", "sister", "steel", 
    "discuss", "forward", "similar", "guide", "experience", "score", "apple", "bought", "led", 
    "pitch", "coat", "mass", "card", "band", "rope", "slip", "win", "dream", "evening", "condition", 
    "feed", "tool", "total", "basic", "smell", "valley", "nor", "double", "seat", "arrive", "master", 
    "track", "parent", "shore", "division", "sheet", "substance", "favor", "connect", "post", 
    "spend", "chord", "fat", "glad", "original", "share", "station", "dad", "bread", "charge", 
    "proper", "bar", "offer", "segment", "slave", "duck", "instant", "market", "degree", "populate", 
    "chick", "dear", "enemy", "reply", "drink", "occur", "support", "speech", "nature", "range", 
    "steam", "motion", "path", "liquid", "log", "meant", "quotient", "teeth", "shell", "neck", 
    "robot", "hacker", "speedrun", "terminal", "python", "easter", "keyboard"
]

class WpmTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Easter Egg: 15s WPM Test")
        self.setMinimumSize(500, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.time_left = 15
        self.is_active = False
        self.correct_chars = 0
        self.current_word_idx = 0
        self.words = random.sample(WORDS, 50)  # Pick 50 random words
        
        self._build_ui()
        self._generate_display_text()
        
    def _build_ui(self):
        layout = QVBoxLayout()
        
        # Header / Timer
        header_layout = QHBoxLayout()
        self.title_lbl = QLabel("⌨️ WPM Speedrun")
        self.title_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.time_lbl = QLabel("Aeg: 15s")
        self.time_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.time_lbl.setStyleSheet("color: #f44336;")
        
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.time_lbl)
        layout.addLayout(header_layout)
        
        # Word display area
        self.display_lbl = QLabel()
        self.display_lbl.setFont(QFont("Consolas", 18))
        self.display_lbl.setWordWrap(True)
        self.display_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_lbl.setStyleSheet("background-color: #2b2b2b; color: #a9b7c6; padding: 20px; border-radius: 8px;")
        layout.addWidget(self.display_lbl)
        
        # Input field
        self.input_edit = QLineEdit()
        self.input_edit.setFont(QFont("Consolas", 16))
        self.input_edit.setPlaceholderText("Alusta trükkimist siia...")
        self.input_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.input_edit)
        
        # Restart / Close buttons
        btn_layout = QHBoxLayout()
        self.restart_btn = QPushButton("Uus katse")
        self.restart_btn.clicked.connect(self._reset_test)
        self.close_btn = QPushButton("Sulge")
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.restart_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

    def _generate_display_text(self, current_input=""):
        """Format the words with colors for typed, current, and upcoming."""
        html = []
        for i, w in enumerate(self.words):
            if i < self.current_word_idx:
                # correctly typed
                html.append(f'<span style="color: #4caf50;">{w}</span>')
            elif i == self.current_word_idx:
                # currently typing
                clean_input = current_input.strip()
                if clean_input and not w.startswith(clean_input):
                    # typo! Red text and underline
                    html.append(f'<span style="color: #f44336; text-decoration: underline;">{w}</span>')
                else:
                    # correct so far, highlight typed letters
                    if clean_input:
                        typed_len = len(clean_input)
                        typed_part = w[:typed_len]
                        rest_part = w[typed_len:]
                        html.append(f'<span style="text-decoration: underline;"><span style="color: #ffffff;">{typed_part}</span><span style="color: #a9b7c6;">{rest_part}</span></span>')
                    else:
                        html.append(f'<span style="color: #ffffff; text-decoration: underline;">{w}</span>')
            else:
                # upcoming
                html.append(f'<span style="color: #757575;">{w}</span>')
        
        self.display_lbl.setText(" ".join(html))

    def _on_text_changed(self, text):
        if not self.is_active and self.time_left == 15 and text.strip():
            # Start timer on first keystroke
            self.is_active = True
            self.timer.start(1000)
            self.input_edit.setPlaceholderText("")

        if not self.is_active:
            return

        target_word = self.words[self.current_word_idx]
        
        # Check if they pressed space to complete a word
        if text.endswith(" "):
            typed_word = text.strip()
            
            if typed_word == target_word:
                self.correct_chars += len(target_word) + 1  # +1 for space
                self.current_word_idx += 1
                
                # Check if they ran out of words (rare in 15s, but possible)
                if self.current_word_idx >= len(self.words):
                    self.words.extend(random.sample(WORDS, 20))
                
                self.input_edit.clear()
                self._generate_display_text()
            else:
                # Provide visual feedback on input field for a missed word
                self.input_edit.setStyleSheet("background-color: #3a1c1c; color: #ff5252;")
                # Keep the space so they are stuck until they fix it
        else:
            clean_input = text.strip()
            if clean_input and not target_word.startswith(clean_input):
                # Error state
                self.input_edit.setStyleSheet("background-color: #3a1c1c; color: #ff5252;")
            else:
                # Normal state
                self.input_edit.setStyleSheet("")
                
            self._generate_display_text(text)

    def _on_tick(self):
        self.time_left -= 1
        self.time_lbl.setText(f"Aeg: {self.time_left}s")
        
        if self.time_left <= 0:
            self._end_test()

    def _end_test(self):
        self.is_active = False
        self.timer.stop()
        self.input_edit.setEnabled(False)
        
        # Calculate WPM based on standard formula: (chars / 5) / time_in_minutes
        # Time is 15 seconds = 0.25 minutes
        wpm = round((self.correct_chars / 5) / 0.25)
        
        self.display_lbl.setText(
            f'<div style="text-align: center;">'
            f'<h2 style="color: #ffffff; margin-bottom: 5px;">Aeg läbi!</h2>'
            f'<h1 style="color: #4caf50; font-size: 36px; margin: 0;">{wpm} WPM</h1>'
            f'<p style="color: #757575;">(15 sekundi jooksul)</p>'
            f'</div>'
        )

    def _reset_test(self):
        self.timer.stop()
        self.time_left = 15
        self.is_active = False
        self.correct_chars = 0
        self.current_word_idx = 0
        self.words = random.sample(WORDS, 50)
        self.time_lbl.setText("Aeg: 15s")
        self.input_edit.clear()
        self.input_edit.setEnabled(True)
        self.input_edit.setPlaceholderText("Alusta trükkimist siia...")
        self.input_edit.setFocus()
        self._generate_display_text()
