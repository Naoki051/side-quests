import os

def print_tree(directory, prefix=""):
    """
    Imprime a estrutura de pastas e arquivos de forma visual,
    ignorando __pycache__ e pastas ocultas.
    """
    # Lista o conteúdo e ignora itens indesejados
    items = [item for item in os.listdir(directory) 
             if item != "__pycache__" and not item.startswith(".")]
    
    # Ordena para pastas aparecerem primeiro que arquivos
    items.sort(key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x))

    for i, item in enumerate(items):
        path = os.path.join(directory, item)
        is_last = (i == len(items) - 1)
        
        # Define os caracteres de ramificação
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{item}")

        # Se for um diretório, mergulha nele (recursividade)
        if os.path.isdir(path):
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(path, new_prefix)

if __name__ == "__main__":
    print(f"\nESTRUTURA DO PROJETO: {os.path.basename(os.getcwd())}")
    print("." )
    print_tree(os.getcwd())