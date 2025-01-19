from collections import Counter
import tokenize
import sys
import io

class Aliases:
    setitem = '_s'

def getIndent(line):
    return (len(line) - len(line.lstrip())) // 4

def parseArgs():
    # Handle args
    infile = sys.argv[1]
    if len(sys.argv) > 2 and not sys.argv[2].startswith('-'):
        outfile = sys.argv[2]
    else:
        outfile = 'out.py'
    return infile, outfile

def removeChars(string,chars):
    for char in chars:
        string = string.replace(char,'')
    return string

def findCommonConstants(code, length):
    tokens = []
    for tok in tokenize.generate_tokens(io.StringIO(code).readline):
        if tok.type in (tokenize.STRING, tokenize.NUMBER):
            tokens.append(tok.string)
    freq = Counter(tokens)
    return [(const,cnt) for const, cnt in freq.items() if cnt > 1 and len(str(const)) > length]

def find_assignment_operator(line):
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == '=' and not in_single and not in_double:
            return i
    return -1

def join(output):
    result = ''
    for line in output:
        if line.strip().startswith('#'):
            result += line + '\n    '
            continue
        if not line.strip():
            result += '\n    '
            continue
        result += line + ',\n    '

    return result

header = '# PyMinifier V0.0.1\n# type: ignore\n'

template = f"""
(
    # Boilerplate
    globals().__setitem__(
        "{Aliases.setitem}", globals().__setitem__
    ),
    <code>
)
"""

constantId = 0
def parse(lines, lastIndent = -1):
    global template, constantId

    skip = 0
    replace = {}
    output = []

    if lastIndent == -1:
        output.append('# Constants')

        for constant, num in findCommonConstants('\n'.join(lines), 8):
            name = f'c{constantId}'
            # _s("<name>",<constant>),
            #  Amount of chars to define it    Characters saved by defining it
            if 8 + len(constant) + len(name) > (len(constant) - len(name))*num:
                continue
            output.append(f'{Aliases.setitem}("{name}",{constant})')
            replace[constant] = name
            constantId += 1

    if lastIndent == -1:
        output.append('# Code')

    for i,line in enumerate(lines):
        if skip:
            skip -= 1
            continue

        indent = getIndent(line)
        line = line.strip()

        if indent == lastIndent:
            return output

        if not line:
            output.append('')
            continue

        print('line:', line)

        if line.endswith(tuple('([{,')):
            skip += 1
            while line.endswith(tuple('([{,')):
                skip += 1
                line += '    '+lines[i+1].strip()
                i += 1
            line += lines[i+1].strip()

        # Import statements
        if line.startswith('import '):
            importName = line.split()[1:]
            if ' as ' in line:
                importName, saveName = importName
            else:
                saveName = importName[0]
            importName = importName[0]
            line = f'{Aliases.setitem}("{saveName}",__import__("{importName}"))'

        # From import statements
        if line.startswith('from '):
            importName = line.split()[1]
            if ' as ' in line:
                importName, saveName = importName
            else:
                saveName = importName
            line = f'{Aliases.setitem}("{saveName}",__import__("{importName}"))'

        elif line.startswith('if '):
            condition = line.removeprefix('if ').removesuffix(':').strip()
            true_branch = parse(lines[i+1:], indent)
            # Check for else block
            else_branch = []
            for j in range(i+1, len(lines)):
                if lines[j].strip().startswith('else:') and getIndent(lines[j]) == indent:
                    else_branch = parse(lines[j+1:], indent)
                    break

            if else_branch:
                line = f'({condition} and ({join(true_branch)},) or ({join(else_branch)},))[0]'
            else:
                line = f'({condition} and ({join(true_branch)},) or (None,))[0]'

        # Functions -> lambdas
        if line.startswith('def '):
            fname, fargs = line.removeprefix('def ').removesuffix('):').split('(')
            fargs = [arg.strip() for arg in fargs.split(',')]
            funcOutput = parse(lines[i+1:], indent)
            # Extract first item from returned tuple
            output.append(f'# Function: {fname}: {fargs}')
            line = f'{fname} = lambda {",".join(fargs)}: ({join(funcOutput)})[0]'

        if line.startswith('class '):
            class_name = line.removeprefix('class ').split('(')[0].strip().removesuffix(':')
            class_body = parse(lines[i+1:], indent)

            # Create empty class
            line = f'{class_name}=type("{class_name}",(),{{}})'

            # Add attributes
            for attr in class_body:
                if '=' in attr:
                    name, value = attr.split('=', 1)
                    output.append(f'setattr({class_name},"{name.strip()}",{value.strip()})')
                else:
                    # Handle methods
                    name = attr.split('(')[0].strip()
                    output.append(f'setattr({class_name},"{name}",{attr})')

        # Return
        if line.startswith('return '):
            value = line.removeprefix('return ').strip()
            line = f'({value},)'

        # Variable assignment
        index = find_assignment_operator(line)
        if index != -1:
            name = line[:index].strip()
            value = line[index+1:].strip()
            line = f'{Aliases.setitem}("{name}", {value})'

        # For loops
        elif line.startswith('for '):
            var, iter_expr = line.removeprefix('for ').removesuffix(':').split(' in ')
            loop_body = parse(lines[i+1:], indent)
            actions = join(loop_body).strip(',\n ')

            # Always wrap in list comprehension with [-1] to get last result
            if ',' in actions:
                line = f'[({actions}) for {var} in {iter_expr}][-1]'
            else:
                line = f'[{actions} for {var} in {iter_expr}][-1]'

            skip += 1

        # While loops
        if line.startswith('while '):
            # while cond: -> (lambda f: f(f))(lambda s: lambda: (cond and (action,s(s)()) or (None,))[0])()
            condition = line.removeprefix('while ').removesuffix(':')
            loop_body = parse(lines[i+1:], indent)
            line = f'(lambda f:f(f))(lambda s:lambda:({condition} and ({join(loop_body)},s(s)()) or (None,)))()'

        for const, name in replace.items():
            line = line.replace(const, name)

        output.append(line)

    if not debug:
        template = removeChars(template, '\n ')

    return output

debug = '--debug' in sys.argv or '-d' in sys.argv

infile, outfile = parseArgs()

# Read file
with open(infile) as f:
    lines = f.readlines()

output = parse(lines)

print(output)

with open(outfile, 'w') as f:
    f.write(header)
    f.write(template.replace('<code>', join(output)))
