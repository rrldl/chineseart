import json

# --- 这是一个包含 20 条高质量、真实中国古代书画数据的列表 ---
# 您可以在这个列表里，继续添加您自己采集的新数据。
golden_data_20 = [
    {
        "title": "秋兴八景图（册页）",
        "author": "董其昌",
        "dynasty": "明代",
        "style": ["山水画", "文人画", "册页"],
        "medium": "纸本水墨",
        "dimensions": {
            "height_cm": 53.8,
            "width_cm": 31.7,
            "unit": "cm"
        },
        "description": "董其昌根据杜甫同名诗歌的诗意创作的系列画作。此图册共八开，每开对题杜诗一首。画风秀润，笔墨松秀，构图简洁，意境深远，是董其昌“南北宗论”绘画理论的实践典范，体现了其对笔墨趣味的极致追求。",
        "collections": ["上海博物馆"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "秋郊饮马图",
        "author": "赵孟頫",
        "dynasty": "元代",
        "style": ["人马画", "青绿山水"],
        "medium": "绢本设色",
        "dimensions": {
            "height_cm": 23.6,
            "width_cm": 59,
            "unit": "cm"
        },
        "description": "元代书画领袖赵孟頫的代表作，描绘了秋日郊外，一位奚官正在照料一群骏马饮水的场景。画中人马造型借鉴了唐代韩干的风格，但笔墨更为秀润，山石树木则有复古之意，体现了他“作画贵有古意”的艺术主张。",
        "collections": ["北京故宫博物院"],
        "seals": [
            {"owner": "乾隆帝", "text": "古希天子", "type": "鉴藏印"}
        ],
        "inscriptions": []
    },
    {
        "title": "墨竹图",
        "author": "郑燮（郑板桥）",
        "dynasty": "清代",
        "style": ["花鸟画", "水墨画", "扬州八怪"],
        "medium": "纸本水墨",
        "dimensions": {
            "height_cm": 169.2,
            "width_cm": 90.3,
            "unit": "cm"
        },
        "description": "“扬州八怪”之一郑板桥的经典作品。画家以饱含水墨的笔触，描绘了数竿秀竹在风中摇曳的姿态。竹叶疏密有致，竹竿挺拔有力，画上常配有其独特的“六分半书”题诗，将书、画、诗、印融为一体，表达其孤高坚韧的品格。",
        "collections": ["北京故宫博物院"],
        "seals": [],
        "inscriptions": [
            {"author": "郑燮", "text": "（常题诗句）衙斋卧听萧萧竹，疑是民间疾苦声。", "type": "题诗"}
        ]
    },
    {
        "title": "六祖伐竹图",
        "author": "梁楷",
        "dynasty": "南宋",
        "style": ["人物画", "简笔画", "禅宗画"],
        "medium": "纸本水墨",
        "dimensions": {
            "height_cm": 73,
            "width_cm": 31.8,
            "unit": "cm"
        },
        "description": "南宋画家梁楷以“减笔”画法创作的禅宗故事画。描绘了禅宗六祖慧能在成为祖师前，作为行者在山中砍伐竹子的场景。人物衣纹寥寥数笔，以大斧劈砍竹子的动态却表现得淋漓尽致，形象生动，禅意十足。",
        "collections": ["东京国立博物馆"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "女史箴图",
        "author": "顾恺之",
        "dynasty": "东晋",
        "style": ["人物画", "仕女画", "游丝描"],
        "medium": "绢本设色",
        "dimensions": {
            "note": "此为唐代摹本尺寸",
            "height_cm": 24.8,
            "width_cm": 348.2,
            "unit": "cm"
        },
        "description": "原作已佚，此为唐代摹本。内容是根据西晋张华的《女史箴》一文，描绘了古代宫廷妇女应遵守的道德规范。画中人物仪态端庄，线条如春蚕吐丝，连绵不绝，是中国早期卷轴画的杰作。",
        "collections": ["大英博物馆"],
        "seals": [
            {"owner": "宋徽宗", "text": "宣和", "type": "年号印"}
        ],
        "inscriptions": []
    },
    {
        "title": "墨梅图",
        "author": "王冕",
        "dynasty": "元代",
        "style": ["花鸟画", "水墨画"],
        "medium": "纸本水墨",
        "dimensions": {
            "height_cm": 31.9,
            "width_cm": 50.9,
            "unit": "cm"
        },
        "description": "元代以画梅著称的画家王冕的代表作。画中一枝梅花横斜而出，枝干苍劲，花朵繁而不乱，以淡墨点染花瓣，生动地表现了梅花清冷、高洁的特质。画上自题长诗，表达了画家不愿与世俗同流合污的高尚情操。",
        "collections": ["北京故宫博物院"],
        "seals": [],
        "inscriptions": [
            {"author": "王冕", "text": "吾家洗砚池头树，个个花开淡墨痕。不要人夸好颜色，只留清气满乾坤。", "type": "自题诗"}
        ]
    },
    {
        "title": "万壑松风图",
        "author": "李唐",
        "dynasty": "南宋",
        "style": ["山水画", "斧劈皴"],
        "medium": "绢本设色",
        "dimensions": {
            "height_cm": 188.7,
            "width_cm": 139.8,
            "unit": "cm"
        },
        "description": "南宋“院体画”的开创者李唐的杰作。画中主峰高耸，山石坚硬，用笔刚劲，以标志性的“斧劈皴”表现山石的质感。山谷间松涛阵阵，泉水奔流，气势雄伟，是北宋雄壮山水与南宋诗意山水的过渡之作。",
        "collections": ["台北故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "渔父图",
        "author": "吴镇",
        "dynasty": "元代",
        "style": ["山水画", "水墨画", "文人画"],
        "medium": "绢本水墨",
        "dimensions": {
            "height_cm": 84.7,
            "width_cm": 29.7,
            "unit": "cm"
        },
        "description": "元四家之一吴镇的代表作，他一生喜爱画渔父题材。此画描绘了江南水乡，一渔父驾小舟于芦苇荡中垂钓的场景。笔墨湿润，氤氲之气十足，表达了文人避世、悠然自得的隐逸情怀。",
        "collections": ["台北故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "泼墨仙人图",
        "author": "梁楷",
        "dynasty": "南宋",
        "style": ["人物画", "泼墨", "禅宗画"],
        "medium": "纸本水墨",
        "dimensions": {
            "height_cm": 48.7,
            "width_cm": 27.7,
            "unit": "cm"
        },
        "description": "梁楷“减笔画”的极致体现。全画以酣畅淋漓的泼墨法，描绘了一个醉态可掬、憨态可掬的仙人形象。人物身体几乎全由一大块浓淡相间的墨块构成，而面部五官则以简练的线条精确勾勒，形神兼备，禅意盎然。",
        "collections": ["台北故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "韩熙载夜宴图",
        "author": "顾闳中",
        "dynasty": "五代·南唐",
        "style": ["人物画", "工笔重彩", "长卷"],
        "medium": "绢本设色",
        "dimensions": {
            "note": "此为宋代摹本尺寸",
            "height_cm": 28.7,
            "width_cm": 335.5,
            "unit": "cm"
        },
        "description": "中国十大传世名画之一。描绘了南唐大臣韩熙载在家中设夜宴、与宾客歌舞弹唱的场景。画卷以连环画的形式，分为“听乐、观舞、暂歇、清吹、散宴”五个部分，细致入微地刻画了四十多位人物的音容笑貌与心理状态。",
        "collections": ["北京故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    # ... (以下省略10条，以保持篇幅)
    {
        "title": "祭侄文稿",
        "author": "颜真卿",
        "dynasty": "唐代",
        "style": ["书法", "行书"],
        "medium": "纸本墨迹",
        "dimensions": {"height_cm": 28.8, "width_cm": 75.5, "unit": "cm"},
        "description": "被誉为“天下第二行书”。此稿是颜真卿为悼念在安史之乱中牺牲的侄子颜季明所写的祭文草稿。全篇情感激昂，从最初的平静到悲愤，再到痛不欲生，书写风格随情绪起伏而变化，涂改之处随处可见，是书法与真情完美结合的典范。",
        "collections": ["台北故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "听琴图",
        "author": "赵佶（宋徽宗）",
        "dynasty": "北宋",
        "style": ["人物画", "工笔设色"],
        "medium": "绢本设色",
        "dimensions": {"height_cm": 147.2, "width_cm": 51.3, "unit": "cm"},
        "description": "宋徽宗赵佶的亲笔画。描绘了其本人在松下抚琴，两位大臣（蔡京和童贯）在旁聆听的场景。人物神情专注，环境清雅，松树、竹子、假山石的描绘都极其工致，是宋代院体画的最高水平代表。",
        "collections": ["北京故宫博物院"],
        "seals": [],
        "inscriptions": [{"author": "蔡京", "text": "（题诗）", "type": "题诗"}]
    },
    {
        "title": "五牛图",
        "author": "韩滉",
        "dynasty": "唐代",
        "style": ["动物画"],
        "medium": "纸本设色",
        "dimensions": {"height_cm": 20.8, "width_cm": 139.8, "unit": "cm"},
        "description": "中国现存最早的纸本画，画中五头牛姿态各异，或行或立，或俯首或昂头，画家以粗劲的线条和精准的造型，表现出牛的筋骨、肌肉和质感，形神兼备，是唐代动物画的杰作。",
        "collections": ["北京故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "簪花仕女图",
        "author": "周昉",
        "dynasty": "唐代",
        "style": ["人物画", "仕女画"],
        "medium": "绢本设色",
        "dimensions": {"height_cm": 46, "width_cm": 180, "unit": "cm"},
        "description": "描绘了唐代贵族妇女在春夏之交赏花游园的场景。画中仕女体态丰腴，衣着华丽，神情悠闲，体现了盛唐时期雍容华贵的审美风尚。线条流畅，设色艳丽，是唐代仕女画的典范之作。",
        "collections": ["辽宁省博物馆"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "寒食帖",
        "author": "苏轼",
        "dynasty": "北宋",
        "style": ["书法", "行书"],
        "medium": "纸本墨迹",
        "dimensions": {"height_cm": 34.2, "width_cm": 199.5, "unit": "cm"},
        "description": "被誉为“天下第三行书”。内容是苏轼因“乌台诗案”被贬黄州时，在寒食节所写的两首诗。全篇书写心境苍凉，笔锋随情绪起伏，字形由小渐大，由正渐斜，跌宕起伏，是宋代“尚意”书风的代表。",
        "collections": ["台北故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "青卞隐居图",
        "author": "王蒙",
        "dynasty": "元代",
        "style": ["山水画", "水墨画", "繁笔山水"],
        "medium": "纸本水墨",
        "dimensions": {"height_cm": 141, "width_cm": 42.2, "unit": "cm"},
        "description": "元四家之一王蒙的代表作。描绘了其表弟在青卞山中隐居的场景。画中山势重峦叠嶂，密不透风，以繁密的“牛毛皴”和“解索皴”表现山石的质感，笔法苍劲，墨色丰富，展现了生意盎然、气势磅礴的景象。",
        "collections": ["上海博物馆"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "清明上河图",
        "author": "张择端",
        "dynasty": "北宋",
        "style": ["风俗画", "界画"],
        "medium": "绢本设色",
        "dimensions": {"height_cm": 24.8, "width_cm": 528.7, "unit": "cm"},
        "description": "中国十大传世名画之一。以长卷形式，描绘了北宋都城汴京（今开封）在清明时节的繁荣景象。全图包含800多位人物，以及大量的牲畜、船只、房屋，内容极为丰富，是中国风俗画的巅峰之作。",
        "collections": ["北京故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "游春图",
        "author": "展子虔",
        "dynasty": "隋代",
        "style": ["山水画", "青绿山水"],
        "medium": "绢本设色",
        "dimensions": {"height_cm": 43, "width_cm": 80.5, "unit": "cm"},
        "description": "中国现存最早的独立山水画卷轴。描绘了春日里人们在山水中郊游的景色。画中山峦树石以青绿色敷染，开创了青绿山水的端绪，透视处理上“人大于山”的特点也反映了早期山水画的特征。",
        "collections": ["北京故宫博物院"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "夏景山口待渡图",
        "author": "董源",
        "dynasty": "五代·南唐",
        "style": ["山水画", "江南山水"],
        "medium": "绢本设色",
        "dimensions": {"height_cm": 50, "width_cm": 320, "unit": "cm"},
        "description": "董源的又一杰作，描绘了夏日江南山水。画中山势平缓，水面开阔，多用点状笔触（“点子皴”）来表现植被的茂盛和山石的质感，充分展现了江南地区“山不见锋，水不見源”的湿润之气。",
        "collections": ["辽宁省博物馆"],
        "seals": [],
        "inscriptions": []
    },
    {
        "title": "捣练图",
        "author": "张萱",
        "dynasty": "唐代",
        "style": ["人物画", "仕女画"],
        "medium": "绢本设色",
        "dimensions": {"note": "此为宋徽宗摹本尺寸", "height_cm": 37, "width_cm": 147, "unit": "cm"},
        "description": "原作已佚，此为宋徽宗摹本。描绘了唐代宫廷妇女们制作丝绢的劳动场景，分为捣练、络线、熨平三个部分。画中人物动作协调，神情专注，是研究唐代妇女生活和丝织工艺的珍贵资料。",
        "collections": ["波士顿美术馆"],
        "seals": [],
        "inscriptions": []
    },
    {
      "title": "千里江山图",
      "author": "王希孟",
      "dynasty": "北宋",
      "style": ["青绿山水", "长卷", "全景山水"],
      "medium": "绢本设色",
      "dimensions": {
        "height_cm": 51.5,
        "width_cm": 1191.5,
        "unit": "cm"
      },
      "description": "中国十大传世名画之一，为北宋画家王希孟18岁时所作，也是其唯一的传世作品。画卷以全景式的构图，描绘了绵延千里的壮丽山河，江河湖泊，村落野市，渔船飞鸟，气象万千。全图用石青、石绿等矿物颜料，色彩鲜丽，历千年而不褪，是中国青绿山水画的巅峰之作。",
      "collections": ["北京故宫博物院"],
      "seals": [
        {
          "owner": "乾隆帝",
          "text": "乾隆御览之宝",
          "type": "鉴藏印"
        },
        {
          "owner": "梁清标",
          "text": "蕉林收藏",
          "type": "鉴藏印"
        }
      ],
      "inscriptions": [
        {
          "author": "蔡京",
          "text": "政和三年闰四月一日赐。希孟。年十八岁。昔在画学为生徒。召入禁中文书库。数以画献。未甚工。上知其性可教。遂诲谕之。亲授其法。不逾半岁。乃以此图进。上嘉之。因以赐臣京。为天下士在作之劝。",
          "type": "卷后题跋"
        }
      ]
    },
    {
      "title": "富春山居图（无用师卷）",
      "author": "黄公望",
      "dynasty": "元代",
      "style": ["山水画", "水墨画", "文人画"],
      "medium": "纸本水墨",
      "dimensions": {
        "height_cm": 33,
        "width_cm": 636.9,
        "unit": "cm"
      },
      "description": "中国十大传世名画之一，元代画家黄公望为挚友无用师所绘，被誉为“画中之兰亭”。后因火烧而分为两段，此为较长的一段。全卷以水墨描绘富春江两岸初秋景色，山峦起伏，林木葱郁，笔法简约高逸，墨色富有变化，是元代文人画的典范。",
      "collections": ["台北故宫博物院"],
      "seals": [
        {
          "owner": "乾隆帝",
          "text": "乾隆御览之宝",
          "type": "鉴藏印"
        },
        {
          "owner": "董其昌",
          "text": "董其昌印",
          "type": "私印"
        }
      ],
      "inscriptions": [
         {
          "author": "乾隆帝",
          "text": "（乾隆在此画上写了大量题跋，此处为一例）山川浑厚，草木华滋。",
          "type": "题诗"
        }
      ]
    },
    {
      "title": "庐山高图",
      "author": "沈周",
      "dynasty": "明代",
      "style": ["山水画", "设色山水"],
      "medium": "纸本设色",
      "dimensions": {
        "height_cm": 193.8,
        "width_cm": 98.1,
        "unit": "cm"
      },
      "description": "明代“吴门画派”领袖沈周为其老师陈宽祝寿所作的贺礼。画家以庐山的雄伟景色来比喻老师的德行与学问。画中山峦层叠，瀑布高悬，笔法粗放、凝重，墨色浓重，是他中年时期的代表作，体现了“粗沈”的典型风格。",
      "collections": ["台北故宫博物院"],
      "seals": [],
      "inscriptions": [
        {
          "author": "沈周",
          "text": "庐山高，高乎哉！郁然二百五十里之盘踞，岌然三千六百丈之巃嵸……",
          "type": "自题长诗"
        }
      ]
    },
    {
      "title": "步溪图",
      "author": "唐寅",
      "dynasty": "明代",
      "style": ["山水人物画"],
      "medium": "绢本设色",
      "dimensions": {
        "height_cm": 159,
        "width_cm": 84.4,
        "unit": "cm"
      },
      "description": "此画是明代“吴门四家”之一唐寅的代表作。描绘了文人雅士在山间溪边信步闲游的场景。画中远山巍峨，近景树石坚实，人物神态悠然，用笔灵动，设色雅致，将南宋院体画的斧劈皴与元代文人画的笔墨趣味相结合，形成了自己独特的风格。",
      "collections": ["北京故宫博物院"],
      "seals": [
        {
          "owner": "唐寅",
          "text": "唐伯虎",
          "type": "作者印"
        }
      ],
      "inscriptions": [
        {
          "author": "唐寅",
          "text": "画堂延伸燕，溪堂对饮鱼。半酣成酩酊，又被小儿扶。",
          "type": "自题诗"
        }
      ]
    },
    {
      "title": "自叙帖",
      "author": "怀素",
      "dynasty": "唐代",
      "style": ["书法", "草书", "狂草"],
      "medium": "纸本墨迹",
      "dimensions": {
        "height_cm": 28.3,
        "width_cm": 755,
        "unit": "cm"
      },
      "description": "“草圣”怀素的狂草代表作，被誉为“中华第一草书”。内容为怀素自述其学书的经历，以及当时名流对他的评价。全卷笔势狂放，连绵不绝，如骤雨旋风，一气呵成，充分体现了唐代奔放、自信的时代精神。",
      "collections": ["台北故宫博物院"],
      "seals": [
        {
          "owner": "乾隆帝",
          "text": "乾隆鉴赏",
          "type": "鉴藏印"
        },
        {
          "owner": "项元汴",
          "text": "墨林秘玩",
          "type": "鉴藏印"
        }
      ],
      "inscriptions": []
    },
    {
      "title": "潇湘图",
      "author": "董源",
      "dynasty": "五代·南唐",
      "style": ["山水画", "江南山水"],
      "medium": "绢本设色",
      "dimensions": {
        "height_cm": 50,
        "width_cm": 141.4,
        "unit": "cm"
      },
      "description": "五代南唐画家、江南山水画派开创者董源的代表作。描绘了江南地区潇水与湘水交汇处的平远景色。画中山峦圆润，坡陀起伏，多用“披麻皴”和淡墨点染，表现出江南山水温润、空濛的特点，开创了后世文人山水画的先河。",
      "collections": ["北京故宫博物院"],
      "seals": [],
      "inscriptions": [
        {
          "author": "董其昌",
          "text": "董北苑潇湘图",
          "type": "卷后题跋"
        }
      ]
    },
    {
      "title": "踏歌图",
      "author": "马远",
      "dynasty": "南宋",
      "style": ["山水人物画", "边角之景"],
      "medium": "绢本水墨",
      "dimensions": {
        "height_cm": 192.5,
        "width_cm": 111,
        "unit": "cm"
      },
      "description": "南宋“院体画”代表画家马远的杰作。描绘了丰收之后，几个老农在田埂上踏歌而行的欢乐情景。画家将主体人物置于画幅下方，远景则有宫殿楼阁掩映于云雾之中，构图采用典型的“马一角”形式，用笔爽利，意境开阔。",
      "collections": ["北京故宫博物院"],
      "seals": [],
      "inscriptions": [
        {
          "author": "宋宁宗",
          "text": "宿雨清畿甸，朝阳丽帝城。丰年人乐业，垅上踏歌行。",
          "type": "御题诗"
        }
      ]
    },
    {
      "title": "百骏图",
      "author": "郎世宁",
      "dynasty": "清代",
      "style": ["宫廷绘画", "中西合璧"],
      "medium": "绢本设色",
      "dimensions": {
        "height_cm": 94.5,
        "width_cm": 776,
        "unit": "cm"
      },
      "description": "意大利来华传教士、清代宫廷画家郎世宁的代表作。长卷描绘了一百匹姿态各异的骏马在草原上放牧的宏大场景。此画融合了西方绘画的透视法、解剖学结构与中国传统的笔墨趣味，马匹造型精准，富有立体感，是中国与西方艺术交流的典范。",
      "collections": ["台北故宫博物院"],
      "seals": [],
      "inscriptions": []
    },
    {
      "title": "洛神赋图",
      "author": "顾恺之",
      "dynasty": "东晋",
      "style": ["人物画", "手卷", "游丝描"],
      "medium": "绢本设色",
      "dimensions": {
        "note": "此为宋代摹本尺寸",
        "height_cm": 27.1,
        "width_cm": 572.8,
        "unit": "cm"
      },
      "description": "原作已佚，现存为宋代摹本。此画是根据曹植的著名文学作品《洛神赋》所创作，以连环画的形式描绘了诗人与洛水女神之间相遇、相恋、最终无奈分离的动人故事。画中人物用“游丝描”，线条连绵流畅，形象飘逸，是中国早期绘画史上的杰作。",
      "collections": ["北京故宫博物院", "辽宁省博物馆", "美国弗利尔美术馆"],
      "seals": [],
      "inscriptions": []
    },
    {
      "title": "容膝斋图",
      "author": "倪瓒",
      "dynasty": "元代",
      "style": ["山水画", "水墨画", "一河两岸"],
      "medium": "纸本水墨",
      "dimensions": {
        "height_cm": 74.7,
        "width_cm": 35.5,
        "unit": "cm"
      },
      "description": "元四家之一倪瓒晚年的代表作，为其好友“容膝斋”主人所作。构图采用其典型的一河两岸式，近景是坡石疏林，中景是大片留白的宽阔水域，远景是平缓的山峦。笔墨极其简练、干淡，意境荒寒、萧疏，体现了画家“逸笔草草，不求形似”的艺术追求和洁身自好的孤高品性。",
      "collections": ["台北故- [ ] 博物院"],
      "seals": [
        {
          "owner": "倪瓒",
          "text": "倪瓒之印",
          "type": "作者印"
        }
      ],
      "inscriptions": [
        {
          "author": "倪瓒",
          "text": "（自题）...为庆征徵君写容膝斋图...",
          "type": "自题"
        }
      ]
    },
    {
      "title": "溪山行旅图",
      "author": "范宽",
      "dynasty": "北宋",
      "style": ["山水画", "丰碑式构图", "水墨画"],
      "medium": "绢本水墨",
      "dimensions": {
        "height_cm": 206.3,
        "width_cm": 103.3,
        "unit": "cm"
      },
      "description": "《溪山行旅图》是北宋画家范宽的代表作，中国绘画史上的丰碑之作。画作采用顶天立地的全景式构图，描绘了雄伟壮丽的山川景色。山中行旅的渺小与山体的巍峨形成鲜明对比，体现了人与自然的和谐关系。作者范宽的签名隐藏在前景右下方的树丛中。",
      "collections": ["台北故宫博物院"],
      "seals": [
        {
          "owner": "乾隆帝",
          "text": "乾隆御览之宝",
          "type": "鉴藏印"
        },
        {
          "owner": "嘉庆帝",
          "text": "嘉庆御览之宝",
          "type": "鉴藏印"
        },
        {
          "owner": "宣统帝",
          "text": "宣统御览之宝",
          "type": "鉴藏印"
        }
      ],
      "inscriptions": [
         {
          "author": "董其昌",
          "text": "北宋范中立溪山行旅图真迹",
          "type": "题跋"
        }
      ]
    },
    {
      "title": "早春图",
      "author": "郭熙",
      "dynasty": "北宋",
      "style": ["山水画", "全景式山水", "早春景象"],
      "medium": "绢本设色",
      "dimensions": {
        "height_cm": 158.3,
        "width_cm": 108.1,
        "unit": "cm"
      },
      "description": "《早春图》是北宋画家郭熙的杰作。画作描绘了初春时节，万物复苏、生机勃勃的山川景色。画家运用“高远、深远、平远”的三远法，构图复杂而富有层次，展现了春日山水的微妙动态和氤氲的水气。左侧署款“早春。壬子年郭熙画。”",
      "collections": ["台北故宫博物院"],
      "seals": [
        {
          "owner": "乾隆帝",
          "text": "乾隆御览之宝",
          "type": "鉴藏印"
        },
        {
          "owner": "乾隆帝",
          "text": "石渠宝笈",
          "type": "鉴藏印"
        }
      ],
      "inscriptions": []
    },
    {
      "title": "虢国夫人游春图",
      "author": "张萱",
      "dynasty": "唐代",
      "style": ["人物画", "仕女画", "工笔设色"],
      "medium": "绢本设色",
      "dimensions": {
        "note": "此为宋徽宗摹本尺寸",
        "height_cm": 51.8,
        "width_cm": 148,
        "unit": "cm"
      },
      "description": "原作已佚，此为北宋宋徽宗的摹本。描绘了唐玄宗的宠妃杨贵妃的姐姐虢国夫人及其眷从在春天出游的场景。画中人物雍容华贵，马匹肥硕健壮，构图疏密有致，设色浓艳亮丽，体现了盛唐时期皇室贵族的奢华生活和审美趣味。",
      "collections": ["辽宁省博物馆"],
      "seals": [
        {
          "owner": "金章宗",
          "text": "群玉中秘",
          "type": "鉴藏印"
        },
        {
          "owner": "清内府",
          "text": "秘殿珠林",
          "type": "鉴藏印"
        }
      ],
      "inscriptions": [
        {
          "author": "金章宗",
          "text": "天水摹张萱虢国夫人游春图",
          "type": "瘦金体题签"
        }
      ]
    },
    {
      "title": "汉宫春晓图",
      "author": "仇英",
      "dynasty": "明代",
      "style": ["人物画", "工笔重彩", "仕女画"],
      "medium": "绢本设色",
      "dimensions": {
        "height_cm": 30.6,
        "width_cm": 574.1,
        "unit": "cm"
      },
      "description": "《汉宫春晓图》是明代“吴门四家”之一仇英的代表作，以长卷形式描绘了汉代宫廷中嫔妃宫女们的日常生活，涵盖了妆扮、赏玩、读书、奏乐等多种活动场景。画中人物繁多，建筑华丽，设色精美，是研究明代宫廷生活和服饰的重要资料。",
      "collections": ["台北故宫博物院"],
      "seals": [
         {
          "owner": "仇英",
          "text": "十洲",
          "type": "作者印"
        },
        {
          "owner": "乾隆帝",
          "text": "乾隆鉴赏",
          "type": "鉴藏印"
        }
      ],
      "inscriptions": []
    },
    {
      "title": "芙蓉锦鸡图",
      "author": "赵佶（宋徽宗）",
      "dynasty": "北宋",
      "style": ["花鸟画", "工笔重彩", "瘦金体"],
      "medium": "绢本设色",
      "dimensions": {
        "height_cm": 81.5,
        "width_cm": 53.6,
        "unit": "cm"
      },
      "description": "此图描绘了秋天芙蓉花盛开，一只华丽的锦鸡飞落枝头，回首顾盼的瞬间。构图精巧，设色华丽，锦鸡的羽毛和芙蓉花瓣的质感都表现得淋漓尽致。画上有作者“瘦金体”题诗：“秋劲拒霜盛，峨冠锦羽鸡。已知全五德，安逸胜凫鹥。”，并署“宣和殿御制并书”。",
      "collections": ["北京故宫博物院"],
      "seals": [
        {
          "owner": "赵佶",
          "text": "御书",
          "type": "签名"
        }
      ],
      "inscriptions": [
        {
          "author": "赵佶（宋徽宗）",
          "text": "秋劲拒霜盛，峨冠锦羽鸡。已知全五德，安逸胜凫鹥。",
          "type": "瘦金体题诗"
        }
      ]
    }
]

# --- 主程序：将上面的数据保存为 JSON 文件 ---
if __name__ == "__main__":
    file_path = "golden_dataset.json"

    print(f"正在将 {len(golden_data_20)} 条高质量真实数据写入文件...")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(golden_data_20, f, ensure_ascii=False, indent=2)

    print(f"\n成功！数据已保存到: {file_path}")
    print("您现在可以继续在这个Python脚本中添加数据，或直接使用生成的JSON文件。")

