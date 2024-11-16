import argparse
import json
import os

from parsernode import FunctionNode


def check_file(entrypoint, srcpath, destpath) -> None:
    if srcpath == destpath:
        raise ValueError('The source and destination files are the same')
    if not os.path.exists(srcpath):
        raise ValueError(f'"{srcpath}" does not exist')
    if not srcpath.endswith('.c'):
        raise ValueError('The file is not a .c file')
    with open(srcpath, 'r', encoding='utf8') as file:
        if entrypoint not in file.read():
            raise ValueError(
                f'The "{entrypoint}" function does not exist in the "{srcpath}"'
            )


def write_to_file(plantuml, filepath) -> None:
    with open(filepath, 'w', encoding='utf8') as file:
        file.write('@startuml\n')
        file.write('skin rose\n\n')
        file.write(f'title {filepath.split('/')[-1]}\n\n')
        for line in plantuml:
            file.write(line)
            file.write('\n')
        file.write('\n@enduml\n')


def main():
    parser = argparse.ArgumentParser(description='Render a graph')
    default_config = os.path.join(
        os.path.dirname(__file__), 'c2puml_config.json'
    )
    parser.add_argument(
        '-c',
        '--config',
        type=str,
        default=default_config,
        help='Provide the path of the json configuration file',
    )

    args = parser.parse_args()
    configpath = args.config
    if not os.path.exists(configpath):
        raise ValueError('No such configuration file!')

    with open(configpath, 'r', encoding='utf8') as file:
        config = json.load(file)
        # Expect config file containing list of json objects
        for graph in config:
            entrypoint = graph['entrypoint']
            srcpath = os.path.expandvars(graph['srcpath'])
            destpath = os.path.expandvars(graph['destpath'])
            check_file(entrypoint, srcpath, destpath)

            entrypoint_node = FunctionNode(entrypoint, srcpath, "")
            print(f'Rendering {entrypoint.split('_')[0]}...')
            plantuml = entrypoint_node.translate()
            write_to_file(plantuml, destpath)
            print(f'Graph saved to {destpath}\n')


if __name__ == '__main__':
    main()
