import customtkinter as ctk

C = {
    'base':    '#0F172A',
    'mantle':  '#0B1120',
    'crust':   '#060D1A',
    'surface0':'#1E293B',
    'surface1':'#334155',
    'surface2':'#475569',
    'overlay0':'#64748B',
    'text':    '#F8FAFC',
    'subtext': '#94A3B8',
    'blue':    '#60A5FA',
    'green':   '#22C55E',
    'yellow':  '#FBBF24',
    'red':     '#EF4444',
    'orange':  '#FB923C',
    'teal':    '#2DD4BF',
    'mauve':   '#C084FC',
    'lavender':'#818CF8',
    'sentinel':'#E8002A',
}

SEVERITY_COLOR = {
    0: C['subtext'],
    1: C['blue'],
    2: C['yellow'],
    3: C['orange'],
    4: C['red'],
}

SEVERITY_LABEL = {
    0: 'Info',
    1: 'Bajo',
    2: 'Medio',
    3: 'Alto',
    4: 'Critico',
}

def apply():
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('blue')
