from json import load
import networkx as nx
from unidecode import unidecode
import gurobipy as gp
from gurobipy import GRB


with open("chinese-xinhua/data/idiom.json") as data_file:
    data = load(data_file)

g = nx.MultiDiGraph()
for item in data:
    word = item["word"]
    pinyin = item["pinyin"].split()

    # 哀莫大于心死
    # assert len(word) == 4, word
    if len(word) != 4:
        continue

    pinyin = {
        "跌宕风流": ["diē", "dàng", "fēng", "liú"],
        "改行自新": ["gǎi", "xíng", "zì", "xīn"],
        "悬龟系鱼": ["xuán", "guī", "jì", "yú"],
        "抓耳搔腮": ["zhuā", "ěr", "sāo", "sāi"],
        "足尺加二": ["zú", "chǐ", "jiā", "èr"],
    }.get(word, pinyin)

    assert len(pinyin) == 4, (word, pinyin)

    g.add_edge(
        # result_0
        word[0],
        word[3],
        #
        # result_1
        # pinyin[0],
        # pinyin[3],
        #
        # result_2
        # unidecode(pinyin[0]),
        # unidecode(pinyin[3]),
        #
        word=word,
        pinyin=" ".join(pinyin),
        explanation=item["explanation"],
    )

l = nx.DiGraph(nx.line_graph(g))
print(l)
m = gp.Model("jielong-v")
words = m.addVars(l.nodes, vtype=GRB.BINARY)
start_words = m.addVars(l.nodes, vtype=GRB.BINARY)
m.addConstr(sum(start_words.values()) == 1)
end_words = m.addVars(l.nodes, vtype=GRB.BINARY)
m.addConstr(sum(end_words.values()) == 1)
# MTZ with general form constraints
# times = m.addVars(l.nodes, vtype=GRB.INTEGER)
# MTZ with linear form constraints
# times = m.addVars(l.nodes, vtype=GRB.INTEGER, ub=len(l) - 1)
steps = m.addVars(l.edges, vtype=GRB.BINARY)
for node in l:
    in_count = sum(steps[edge] for edge in l.in_edges(node))
    out_count = sum(steps[edge] for edge in l.out_edges(node))
    m.addConstr(in_count <= 1)
    m.addConstr(words[node] <= start_words[node] + in_count)
    m.addConstr(out_count - in_count == start_words[node] - end_words[node])

# one-shot MTZ
# for edge in l.edges:
#     # general form
#     # m.addConstr((steps[edge] == 1) >> (times[edge[1]] >= times[edge[0]] + 1))
#     # linear form
#     # m.addConstr(times[edge[1]] >= times[edge[0]] + 1 + (len(l) - 1) * (steps[edge] - 1))

while True:
    m.setObjective(sum(words.values()), GRB.MAXIMIZE)
    m.optimize()

    start_word = [node for node, var in start_words.items() if var.x == 1][0]
    g_words = l.edge_subgraph(edge for edge, var in steps.items() if var.x == 1)
    print(g_words)

    g_result = None
    subtours = []
    for component in nx.connected_components(nx.MultiGraph(g_words)):
        if start_word in component:
            assert not g_result
            g_result = g_words.subgraph(component)
        else:
            subtours.append(g_words.subgraph(component))
    print(g_result, "with subtours count:", len(subtours))
    # assert not subtours
    if not subtours:
        break

    # iterative
    # for subtour in subtours:
    #     # MTZ
    #     # for edge in subtour.edges:
    #     #     # general form
    #     #     # m.addConstr((steps[edge] == 1) >> (times[edge[1]] >= times[edge[0]] + 1))
    #     #     # linear form
    #     #     # m.addConstr(
    #     #     #     times[edge[1]] >= times[edge[0]] + 1 + (len(l) - 1) * (steps[edge] - 1)
    #     #     # )
    #     # subtour elimination constraints
    #     m.addConstr(len(subtour.edges) >= sum(steps[edge] for edge in subtour.edges) + 1)

    break  # tolerance subtours in result

word = start_word
end_word = [node for node, var in end_words.items() if var.x == 1][0]
while True:
    w = g.edges[word]
    print(f"{w['word']:10}{w['pinyin']:30}{w['explanation']}")
    if word == end_word:
        break
    next_words = g_result.succ[word]
    assert len(next_words) == 1, (word, next_words)
    word = next(iter(next_words))
