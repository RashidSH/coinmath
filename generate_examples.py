# -*- coding: utf-8 -*-

import math
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


def generate_example(level):
    answer, s, draw_data = gen(level)

    image = Image.new('RGBA', (700, 540))

    frame = Image.open('assets/frame.png')
    image.paste(frame)

    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype('assets/Arcon-Regular.otf', 84)

    if level in (11, 12):
        center = image.height // 2

        draw.line((170, center, 270, center), (0, 0, 0), 5)
        draw.line((430, center, 530, center), (0, 0, 0), 5)
        draw.text((330, center - 60), draw_data[0], (0, 0, 0), font=font)

        x1 = 200 if draw_data[1] < 10 else 185
        x2 = 200 if draw_data[2] < 10 else 185
        x3 = 460 if draw_data[3] < 10 else 445
        x4 = 460 if draw_data[4] < 10 else 445

        draw.text((x1, center - 110), str(draw_data[1]), (0, 0, 0), font=font)
        draw.text((x2, center + 10), str(draw_data[2]), (0, 0, 0), font=font)
        draw.text((x3, center - 110), str(draw_data[3]), (0, 0, 0), font=font)
        draw.text((x4, center + 10), str(draw_data[4]), (0, 0, 0), font=font)

    else:
        text = s.replace(' ', '')

        width, height = draw.multiline_textsize(text, font=font)

        if level == 8 or level == 9:
            offset = 170
        else:
            offset = 210

        draw.multiline_text((350 - width // 2, offset), text, (0, 0, 0), font=font, align='center')

    buf = BytesIO()
    image.save(buf, format='png')
    buf.seek(0)

    return answer, s, buf


def gen(level):
    draw_data = None

    if level == 1:
        m1 = random.randint(1, 20)
        m2 = random.randint(1, 20)
        op = random.randint(1, 2)

        if op == 1:
            op_str = '+'
        else:
            op_str = '-'
            if m1 < m2:
                m1, m2 = m2, m1

        s = f'{m1} {op_str} {m2}'

    elif level == 2:
        m1 = random.randint(2, 10)
        m2 = random.randint(2, 10)
        op = random.randint(1, 2)

        if op == 1:
            op_str = '*'
        else:
            op_str = '/'
            m1 *= m2

        s = f'{m1} {op_str} {m2}'

    elif level == 3:
        m1 = random.randint(8, 30)
        m2 = random.randint(8, 30)
        op = random.randint(1, 4)

        if op == 1:
            op_str = '+'
        elif op == 2:
            op_str = '-'
            if m1 < m2:
                m1, m2 = m2, m1
        elif op == 3:
            op_str = '*'
        else:
            op_str = '/'
            m1 *= m2

        s = f'{m1} {op_str} {m2}'

    elif level == 4:
        ops = ('+', '-', '*')
        m1 = random.randint(5, 25)
        m2 = random.randint(5, 25)
        m3 = random.randint(5, 25)
        op1 = random.choice(ops)
        op2 = random.choice(ops)

        s = f'{m1} {op1} {m2} {op2} {m3}'

    elif level == 5:
        ops = ('+', '-', '*')
        m1 = random.randint(4, 20)
        m2 = random.randint(4, 20)
        m3 = random.randint(4, 20)
        m4 = random.randint(2, 5)
        p4 = random.randint(1, 3)
        op1 = random.choice(ops)
        op2 = random.choice(ops)

        s4 = '/' + str(m4)
        if p4 == 1:
            m1 *= m4
            m1 = str(m1) + s4
        elif p4 == 2:
            m2 *= m4
            m2 = str(m2) + s4
        else:
            m3 *= m4
            m3 = str(m3) + s4

        s = f'{m1} {op1} {m2} {op2} {m3}'

    elif level == 6:
        ops = ('+', '-')
        m1 = random.randint(4, 20)
        m2 = random.randint(4, 20)
        m3 = random.randint(2, 11)
        p = random.randint(1, 2)
        op1 = random.choice(ops)

        s1 = f'({m1} {op1} {m2})'

        if p == 1:
            s = f'{s1} * {m3}'
        else:
            s = f'{m3} * {s1}'

    elif level == 7:
        ops = ('+', '-')
        m1 = random.randint(4, 11)
        m2 = random.randint(4, 11)
        m3 = random.randint(2, 11)
        p1 = random.randint(1, 2)
        p2 = random.randint(1, 3)
        op1 = random.choice(ops)

        if p2 == 1:
            m1 = str(m1) + '**2'
        elif p2 == 2:
            m2 = str(m2) + '**2'
        else:
            m3 = str(m3) + '**2'

        s1 = f'({m1} {op1} {m2})'

        if p1 == 1:
            s = f'{s1} * {m3}'
        else:
            s = f'{m3} * {s1}'

    elif level == 8:
        ops = ('+', '-')
        m1 = random.randint(2, 10)
        m2 = random.randint(2, 10)
        x = random.randint(2, 10)
        p = random.randint(1, 2)
        op1 = random.choice(ops)

        if p == 1:
            s1 = f'{m1}x {op1} {m2}'
        else:
            s1 = f'{m1} {op1} {m2}x'

        s = f"{s1}={eval(s1.replace('x', '*' + str(x)))}\nx=?"
        answer = x

    elif level == 9:
        ops = ('+', '-', '*', '/')
        m1 = random.randint(3, 15)
        m2 = random.randint(3, 15)
        x = random.randint(3, 15)
        p = random.randint(1, 2)
        op1 = random.choice(ops)

        if op1 == '/':
            if p == 2:
                p = 1

            m2 //= 2
            x //= 2
            x *= m2

        if p == 1:
            s1 = f'{m1}x {op1} {m2}'
        else:
            s1 = f'{m1} {op1} {m2}x'

        s = f"{s1}={int(eval(s1.replace('x', '*' + str(x))))}\nx=?"
        answer = x

    elif level == 10:
        ops = ('+', '-', '*')
        m1 = random.randint(3, 10)
        m2 = random.randint(3, 10)
        m3 = random.randint(2, 10)
        m4 = random.randint(2, 3)
        p1 = random.randint(1, 2)
        p2 = random.randint(1, 3)
        op1 = random.choice(ops)

        if p2 == 1:
            m1 = f'{m1 // 2}**{m4}'
        elif p2 == 2:
            m1 = f'{m2 // 2}**{m4}'
        else:
            m1 = f'{m3 // 2}**{m4}'

        s1 = f'({m1} {op1} {m2})'

        if p1 == 1:
            s = f'{s1} * {m3}'
        else:
            s = f'{m3} * {s1}'

    elif level == 11:
        ops = ('+', '-')
        m1 = random.randint(1, 10)
        m2 = random.randint(1, 10)
        d1 = random.randint(2, 20)
        mult = random.randint(1, 3)
        p = random.randint(1, 2)
        op = random.choice(ops)

        if op == '+':
            res1, res2 = m1 + m2, d1
        else:
            res1, res2 = m1 - m2, d1

        k = math.gcd(res1, res2)

        if res2 // k == 1:
            answer = str(res1 // k)
        else:
            answer = f'{res1 // k}/{res2 // k}'

        m2 *= mult
        d2 = d1 * mult

        if p == 2 and op == '+':
            m1, m2, d1, d2 = m2, m1, d2, d1

        s = f'{m1}/{d1} {op} {m2}/{d2}=?'
        draw_data = (op, m1, d1, m2, d2)

    elif level == 12:
        ops = ('*', '/')
        m1 = random.randint(1, 10)
        m2 = random.randint(1, 10)
        d1 = random.randint(2, 10)
        d2 = random.randint(2, 10)
        mult = random.randint(1, 3)
        p = random.randint(1, 4)
        op = random.choice(ops)

        if p == 1:
            m1 *= mult
        elif p == 2:
            m2 *= mult
        elif p == 3:
            d1 *= mult
        else:
            d2 *= mult

        if op == '*':
            res1 = m1 * m2
            res2 = d1 * d2
        else:
            res1 = m1 * d2
            res2 = d1 * m2

        k = math.gcd(res1, res2)

        if res2 // k == 1:
            answer = str(res1 // k)
        else:
            answer = f'{res1 // k}/{res2 // k}'

        if p == 2 and op == '*':
            m1, m2, d1, d2 = m2, m1, d2, d1

        s = f'({m1}/{d1}) {op} ({m2}/{d2})=?'
        draw_data = (op, m1, d1, m2, d2)

    else:
        raise ValueError('Этот уровень не существует.')

    if level not in (8, 9, 11, 12):
        answer = int(eval(s))
        s = s.replace('**2', '²').replace('**3', '³') + '=?'

    return answer, s, draw_data
