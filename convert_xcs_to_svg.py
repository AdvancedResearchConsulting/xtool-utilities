#!/usr/bin/env python3
"""Convert xTool Creative Space .xcs file to SVG."""

import json
import math
import base64
import sys

def int_color_to_hex(color_val):
    """Convert integer color (like 16421416) or hex string to CSS color."""
    if isinstance(color_val, str):
        if color_val.startswith('#'):
            return color_val
        try:
            color_val = int(color_val)
        except:
            return color_val
    if isinstance(color_val, (int, float)):
        color_val = int(color_val)
        r = (color_val >> 16) & 0xFF
        g = (color_val >> 8) & 0xFF
        b = color_val & 0xFF
        return f'#{r:02x}{g:02x}{b:02x}'
    return '#000000'

def get_fill_color(display):
    """Get fill color from display object."""
    fill = display.get('fill', {})
    if not fill.get('visible', False):
        return 'none'
    color = fill.get('color', 0)
    alpha = fill.get('alpha', 1)
    hex_color = int_color_to_hex(color)
    if alpha < 1:
        return hex_color  # could add opacity attr separately
    return hex_color

def get_stroke_props(display):
    """Get stroke properties from display object."""
    stroke = display.get('stroke', {})
    if not stroke.get('visible', False):
        return None
    color = stroke.get('color', 0)
    alpha = stroke.get('alpha', 1)
    width = stroke.get('width', 1)
    cap = stroke.get('cap', 'butt')
    join = stroke.get('join', 'miter')
    return {
        'color': int_color_to_hex(color),
        'width': width,
        'alpha': alpha,
        'cap': cap,
        'join': join,
    }

def build_transform(display):
    """Build SVG transform string from display properties."""
    x = display.get('x', 0)
    y = display.get('y', 0)
    angle = display.get('angle', 0)
    scale = display.get('scale', {'x': 1, 'y': 1})
    sx = scale.get('x', 1)
    sy = scale.get('y', 1)
    
    transforms = []
    transforms.append(f'translate({x}, {y})')
    
    if angle != 0:
        angle_deg = angle * 180 / math.pi if abs(angle) > 2 * math.pi else angle
        # xTool uses radians
        angle_deg = angle * 180 / math.pi
        transforms.append(f'rotate({angle_deg})')
    
    if sx != 1 or sy != 1:
        transforms.append(f'scale({sx}, {sy})')
    
    return ' '.join(transforms)

def render_path(display):
    """Render a PATH display as SVG path element."""
    dpath = display.get('dPath', '')
    if not dpath:
        return ''
    
    transform = build_transform(display)
    fill = get_fill_color(display)
    stroke_props = get_stroke_props(display)
    fill_rule = display.get('fillRule', 'nonzero')
    
    attrs = [f'd="{dpath}"']
    attrs.append(f'fill="{fill}"')
    if fill_rule:
        attrs.append(f'fill-rule="{fill_rule}"')
    
    if stroke_props:
        attrs.append(f'stroke="{stroke_props["color"]}"')
        attrs.append(f'stroke-width="{stroke_props["width"]}"')
        attrs.append(f'stroke-linecap="{stroke_props["cap"]}"')
        attrs.append(f'stroke-linejoin="{stroke_props["join"]}"')
        if stroke_props['alpha'] < 1:
            attrs.append(f'stroke-opacity="{stroke_props["alpha"]}"')
    else:
        attrs.append('stroke="none"')
    
    fill_obj = display.get('fill', {})
    if fill_obj.get('alpha', 1) < 1:
        attrs.append(f'fill-opacity="{fill_obj["alpha"]}"')
    
    return f'<path transform="{transform}" {" ".join(attrs)} />'

def render_rect(display):
    """Render a RECT display as SVG rect element."""
    w = display.get('width', 0)
    h = display.get('height', 0)
    r = display.get('radius', 0)
    
    transform = build_transform(display)
    fill = get_fill_color(display)
    stroke_props = get_stroke_props(display)
    
    attrs = [f'x="{-w/2}" y="{-h/2}" width="{w}" height="{h}"']
    if r > 0:
        attrs.append(f'rx="{r}" ry="{r}"')
    attrs.append(f'fill="{fill}"')
    
    if stroke_props:
        attrs.append(f'stroke="{stroke_props["color"]}"')
        attrs.append(f'stroke-width="{stroke_props["width"]}"')
    else:
        attrs.append('stroke="none"')
    
    return f'<rect transform="{transform}" {" ".join(attrs)} />'

def render_line(display):
    """Render a LINE display as SVG line element."""
    endpoint = display.get('endPoint', {})
    x2 = endpoint.get('x', 0)
    y2 = endpoint.get('y', 0)
    
    transform = build_transform(display)
    stroke_props = get_stroke_props(display)
    
    if not stroke_props:
        stroke_props = {'color': '#000000', 'width': 1, 'cap': 'butt', 'join': 'miter', 'alpha': 1}
    
    attrs = [f'x1="0" y1="0" x2="{x2}" y2="{y2}"']
    attrs.append(f'stroke="{stroke_props["color"]}"')
    attrs.append(f'stroke-width="{stroke_props["width"]}"')
    
    return f'<line transform="{transform}" {" ".join(attrs)} />'

def render_bitmap(display):
    """Render a BITMAP display as SVG image element."""
    b64 = display.get('base64', '')
    if not b64:
        return ''
    
    w = display.get('width', 0)
    h = display.get('height', 0)
    transform = build_transform(display)
    
    return f'<image transform="{transform}" x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" href="{b64}" />'

def render_text(display):
    """Render a TEXT display - convert to path via charJSONs if available, else placeholder."""
    # xTool stores text as charJSONs with path data sometimes
    char_jsons = display.get('charJSONs', [])
    text_content = display.get('text', '')
    
    transform = build_transform(display)
    fill = get_fill_color(display)
    
    style = display.get('style', {})
    font_size = style.get('fontSize', 12)
    font_family = style.get('fontFamily', 'sans-serif')
    
    w = display.get('width', 0)
    h = display.get('height', 0)
    
    # Try to render as SVG text
    attrs = [f'font-size="{font_size}"', f'font-family="{font_family}"']
    attrs.append(f'fill="{fill}"')
    
    return f'<text transform="{transform}" {" ".join(attrs)}>{text_content}</text>'

def convert_canvas_to_svg(canvas, canvas_index):
    """Convert a single canvas to SVG."""
    displays = canvas.get('displays', [])
    if not displays:
        return None
    
    # Determine bounding box
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')
    
    for d in displays:
        if not d.get('visible', True):
            continue
        x = d.get('x', 0)
        y = d.get('y', 0)
        w = d.get('width', 0)
        h = d.get('height', 0)
        sx = abs(d.get('scale', {}).get('x', 1))
        sy = abs(d.get('scale', {}).get('y', 1))
        
        # Estimate bounds
        half_w = w * sx / 2 + 1
        half_h = h * sy / 2 + 1
        min_x = min(min_x, x - half_w)
        min_y = min(min_y, y - half_h)
        max_x = max(max_x, x + half_w)
        max_y = max(max_y, y + half_h)
    
    if min_x == float('inf'):
        return None
    
    padding = 2
    min_x -= padding
    min_y -= padding
    max_x += padding
    max_y += padding
    
    vw = max_x - min_x
    vh = max_y - min_y
    
    # Sort by zOrder
    sorted_displays = sorted(displays, key=lambda d: d.get('zOrder', 0))
    
    elements = []
    for d in sorted_displays:
        if not d.get('visible', True):
            continue
        
        dtype = d.get('type', '')
        try:
            if dtype == 'PATH':
                el = render_path(d)
            elif dtype == 'RECT':
                el = render_rect(d)
            elif dtype == 'LINE':
                el = render_line(d)
            elif dtype == 'BITMAP':
                el = render_bitmap(d)
            elif dtype == 'TEXT':
                el = render_text(d)
            else:
                continue
            if el:
                elements.append(el)
        except Exception as e:
            print(f'Warning: Failed to render {dtype}: {e}', file=sys.stderr)
    
    if not elements:
        return None
    
    # Use mm units since xTool works in mm
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="{min_x} {min_y} {vw} {vh}"
     width="{vw}mm" height="{vh}mm">
  <title>Canvas {canvas_index}: {canvas.get("title", "untitled")}</title>
'''
    
    # Group by layer
    for el in elements:
        svg += f'  {el}\n'
    
    svg += '</svg>\n'
    return svg

def main():
    with open('/mnt/user-data/uploads/Calib-Slides.xcs') as f:
        data = json.load(f)
    
    for i, canvas in enumerate(data['canvas']):
        ext = canvas.get('extendInfo', {})
        canvas_type = ext.get('type', '2d')
        title = canvas.get('title', f'canvas_{i}')
        displays = canvas.get('displays', [])
        
        visible_count = sum(1 for d in displays if d.get('visible', True))
        print(f'Canvas {i} ({title}): type={canvas_type}, {len(displays)} displays ({visible_count} visible)')
        
        if canvas_type == '2d' or True:  # Process all canvases with 2D displays
            svg = convert_canvas_to_svg(canvas, i)
            if svg:
                fname = f'/home/claude/canvas_{i}.svg'
                with open(fname, 'w') as f:
                    f.write(svg)
                print(f'  -> Wrote {fname}')
    
    # Also create a combined SVG with all visible 2D canvases
    # Focus on canvas 1 which has the main content
    canvas1 = data['canvas'][1]
    svg1 = convert_canvas_to_svg(canvas1, 1)
    if svg1:
        out_path = '/mnt/user-data/outputs/Calib-Slides.svg'
        with open(out_path, 'w') as f:
            f.write(svg1)
        print(f'\nMain output: {out_path}')

if __name__ == '__main__':
    main()
