"""destaque.py: qual palavra de uma frase vira o destaque (a palavra grande, na serifa).

A regra, de propósito simples (sem dicionário de classes gramaticais):
1. Fora as palavras vazias de português e inglês (artigos, preposições, pronomes, conjunções, verbos de ligação e
   auxiliares, advérbios de tempo e de lugar comuns e muletas como "tipo", "coisa", "gente"), os números e as palavras
   com menos de 4 letras.
2. Fora os advérbios em "-mente" e "-ly" quando sobra outra candidata: o peso fica no substantivo ou no verbo.
3. Entre as que sobram, a mais longa. Empate: a mais perto do fim da frase (onde a fala costuma pôr a ênfase).
4. Sem candidata, a frase fica sem destaque.

A pessoa sobrescreve pelo `destaques.txt` do projeto (ver `caso.py aplicar`): uma linha por frase, com as palavras em
destaque entre colchetes.
"""
import re
import unicodedata

VAZIAS = set("""
a à ao aos as às o os um uma uns umas de do da dos das dum duma em no na nos nas num numa por pelo pela pelos pelas
para pra pro pras pros com sem sob sobre entre até após desde contra perante e ou mas nem que se porque pois porém
como quando onde enquanto embora então logo também ainda já só sim não nao eu tu ele ela nós vós eles elas você vocês
voce voces me te se lhe lhes nos vos mim ti si comigo contigo meu minha meus minhas teu tua teus tuas seu sua seus suas
nosso nossa nossos nossas dele dela deles delas esse essa esses essas este esta estes estas isso isto aquele aquela
aqueles aquelas aquilo aqui aí ali lá cá agora hoje ontem amanhã sempre nunca muito muita muitos muitas pouco pouca
mais menos bem mal tão tanto tanta todo toda todos todas tudo nada algo alguém ninguém cada outro outra outros outras
mesmo mesma qual quais quem cujo onde é são era eram foi foram ser sou somos estar estou está estão estava estavam
esteve tem têm tenho temos tinha ter haver há havia vai vou vamos vão ia faz fazer feito fez pode posso podem poder
quer quero deve dever tipo coisa coisas gente cara né ok aí daí entendeu sabe olha assim então daqui disso disto
nisso nisto desse dessa deste desta nesse nessa neste nesta naquele naquela pra pras numa nuns
the a an and or but so nor yet of to in on at for with by from as into onto over under about after before than then
there here this that these those it its it's i i'm i've i'd you you're your yours he she we they me my mine him her his
hers our ours their theirs them us is am are was were be been being do does did done have has had having will would
shall should can could may might must not no yes just very really what when where who whom whose how which why also
only even every each most more much many some any all both either neither other another such own same too again ever
never always now today well like get got gets going gonna wanna thing things stuff kind sort yeah okay ok right
""".split())


def limpa(t):
    return re.sub(r"[^\w'’-]+", "", t, flags=re.UNICODE).strip("-'’")


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


VAZIAS_SEM_ACENTO = {_sem_acento(v) for v in VAZIAS}


def vazia(t):
    w = limpa(t).lower()
    return not w or _sem_acento(w) in VAZIAS_SEM_ACENTO or w.isdigit()


def escolhe(textos):
    """índice da palavra em destaque numa frase (lista de textos), ou -1"""
    cand = [i for i, t in enumerate(textos) if not vazia(t) and len(limpa(t)) >= 4]
    sem_adv = [i for i in cand if not re.search(r"(mente|ly)$", limpa(textos[i]).lower())]
    cand = sem_adv or cand
    if not cand:
        return -1
    return max(cand, key=lambda i: (len(limpa(textos[i])), i))


if __name__ == "__main__":  # autoteste
    assert escolhe("eu sempre quis mudar de vida".split()) == 3, "mudar (5) > sempre (vazia) e vida (4)"
    assert escolhe("and go and reinvent myself".split()) == 3
    assert escolhe("isso é muito rapidamente feito".split()) == 3, "só sobra o advérbio: ele fica"
    assert escolhe("o que tu acha".split()) == 3  # "acha" é a única candidata
    assert escolhe("é o que é".split()) == -1
    assert escolhe("trabalho constante cria resultado".split()) == 3, "empate de 9 letras: a mais perto do fim"
    assert escolhe("realmente funciona".split()) == 1, "advérbio em -mente perde"
    print("destaque.py: autoteste passou")
