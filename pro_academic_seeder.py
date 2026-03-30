from py2neo import Graph, Node, Relationship

graph = Graph("bolt://localhost:7687", auth=("neo4j", "12345678"))

# 定义真实的美术史数据
art_data = {
    "晋唐": {
        "artists": ["顾恺之", "阎立本", "吴道子", "王维", "张萱", "周昉"],
        "works": ["洛神赋图", "步辇图", "送子天王图", "伏生授经图", "捣练图", "簪花仕女图"]
    },
    "五代两宋": {
        "artists": ["顾闳中", "荆浩", "关仝", "范宽", "郭熙", "张择端", "王希孟", "苏轼", "米芾", "李唐", "马远", "夏圭"],
        "works": ["韩熙载夜宴图", "匡庐图", "溪山行旅图", "早春图", "清明上河图", "千里江山图", "枯木怪石图", "万壑松风图"]
    },
    "元代": {
        "artists": ["赵孟頫", "黄公望", "王蒙", "倪瓒", "吴镇"],
        "works": ["鹊华秋色图", "富春山居图", "青卞隐居图", "六君子图", "洞庭渔隐图"]
    },
    "明清": {
        "artists": ["沈周", "文徵明", "唐寅", "仇英", "董其昌", "朱耷", "石涛", "郑板桥", "郎世宁"],
        "works": ["庐山高图", "湘君湘夫人图", "落花诗意图", "汉宫春晓图", "秋兴八景图", "荷花水禽图", "万点恶墨图", "兰竹石图", "百骏图"]
    }
}

print("正在构建学术级书画知识图谱...")

for period_name, content in art_data.items():
    # 创建时期节点
    p_node = graph.nodes.match("Period", name=period_name).first()
    if not p_node:
        p_node = Node("Period", name=period_name)
        graph.create(p_node)

    for name in content["artists"]:
        a = Node("Artist", name=name, info=f"中国美术史{period_name}代表人物")
        graph.create(a)
        graph.create(Relationship(a, "所属时期", p_node))
    
    for work in content["works"]:
        w = Node("Artwork", name=work, detail=f"{period_name}时期传世经典")
        graph.create(w)
        graph.create(Relationship(w, "创作于", p_node))

print("学术基础数据录入完成！")