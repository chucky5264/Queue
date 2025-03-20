from collections import deque, OrderedDict

waiting_list = deque(range(1, 3001))      # Liste d'attente des numéros disponibles
registered_queue = deque()                # File d'attente des participants inscrits via QR code
active_counters = OrderedDict()           # Dernier numéro appelé par chaque comptoir
