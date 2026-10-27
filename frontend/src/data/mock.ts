import type { Book, Chapter, Character, Hook, TimelineEvent, WorldBuilding, OutlineNode, WorkflowState, QualityScore, TokenBudget, ReviewReport, RecentActivity, BeatPoint } from '../types'

export const mockBooks: Book[] = [
  {
    id: 'book-1',
    title: '星辰大陆',
    genre: '玄幻',
    description: '一个少年从边陲小镇崛起，踏上修炼星辰之力、探索大陆秘密的传奇旅程。在这个以星力为尊的世界，他将揭开远古诸神陨落之谜。',
    total_words: 156800,
    total_chapters: 8,
    active_hooks: 5,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-06-20T14:30:00Z',
  },
  {
    id: 'book-2',
    title: '量子深渊',
    genre: '科幻',
    description: '2187年，人类发现量子维度中存在着另一个文明的痕迹。一支由物理学家和特种兵组成的探险队深入量子深渊，面对的是超越三维认知的一切。',
    total_words: 89200,
    total_chapters: 5,
    active_hooks: 3,
    created_at: '2025-03-01T08:00:00Z',
    updated_at: '2025-06-18T09:15:00Z',
  },
]

export const mockCharacters: Character[] = [
  // 星辰大陆角色
  {
    id: 'char-1',
    book_id: 'book-1',
    name: '林昊',
    role: '主角',
    tag: '少年成长/星辰师',
    avatar_color: '#ffffff',
    portrait: '十七岁少年，黑发星眸，身形清瘦但眼神坚毅。左臂有一道星纹胎记，是他血脉觉醒的标记。',
    personality: '外冷内热，沉默寡言但重情重义。面对压迫时展现出惊人的韧性，对朋友极度忠诚。有时过于固执，不愿求助他人。',
    background: '出身于星辰大陆边陲的落星镇，父母在他五岁时神秘消失。由爷爷林老抚养长大，自幼被镇上人嘲笑为"废脉少年"。',
    motivation: '寻找父母下落，证明自己的价值，保护所爱之人。深层动机是解开自身血脉之谜。',
    abilities: '星辰之力（初期：引星境）；特殊能力：星纹觉醒后可吞噬他人星力。成长型能力，随着剧情解锁新形态。',
    catchphrase: '我不需要天赋来定义我是谁。',
    growth_arc: [
      { id: 'ga1', chapter_range: '1-3', description: '废脉少年，在镇中受辱，觉醒星纹', milestone: '觉醒' },
      { id: 'ga2', chapter_range: '4-6', description: '进入星辰学院，初露锋芒', milestone: '成长' },
      { id: 'ga3', chapter_range: '7-8', description: '揭开父母线索，踏上更大的舞台', milestone: '蜕变' },
    ],
    relationships: [
      { target_id: 'char-2', target_name: '苏瑶', type: '羁绊', description: '青梅竹马，暗中倾慕' },
      { target_id: 'char-3', target_name: '赵无极', type: '对手', description: '学院中的宿敌，出身名门' },
      { target_id: 'char-4', target_name: '林老', type: '亲情', description: '抚养他长大的爷爷' },
    ],
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-06-20T14:30:00Z',
  },
  {
    id: 'char-2',
    book_id: 'book-1',
    name: '苏瑶',
    role: '女主',
    tag: '天才少女/治愈系',
    avatar_color: '#cccccc',
    portrait: '十六岁少女，长发如瀑，容颜清丽。常着淡蓝色星袍，腰间挂着一枚银色铃铛。',
    personality: '温柔聪慧，善解人意，但在关键时刻展现出惊人的决断力。对林昊有着无条件的信任。',
    background: '星辰学院院长的孙女，自幼被当作天才培养。五岁时曾在落星镇游玩，与小林昊结下缘分。',
    motivation: '守护身边的人，追寻星辰之道的真谛。隐藏着对自身命运的抗争。',
    abilities: '星辰治愈术（天赋极高）；特殊能力：银铃可预知危险。',
    catchphrase: '我相信你，从始至终。',
    growth_arc: [
      { id: 'ga1', chapter_range: '1-3', description: '以学院天才身份登场，暗中关注林昊', milestone: '重逢' },
      { id: 'ga2', chapter_range: '4-6', description: '与林昊并肩作战，感情升温', milestone: '并肩' },
      { id: 'ga3', chapter_range: '7-8', description: '揭示身世秘密，面临抉择', milestone: '觉醒' },
    ],
    relationships: [
      { target_id: 'char-1', target_name: '林昊', type: '羁绊', description: '青梅竹马，默默守护' },
      { target_id: 'char-3', target_name: '赵无极', type: '同门', description: '学院同门，被其追求但婉拒' },
    ],
    created_at: '2025-01-16T10:00:00Z',
    updated_at: '2025-06-19T14:30:00Z',
  },
  {
    id: 'char-3',
    book_id: 'book-1',
    name: '赵无极',
    role: '反派/对手',
    tag: '名门天骄/亦正亦邪',
    avatar_color: '#666666',
    portrait: '十八岁青年，面容英俊但眼神高傲。身着华丽金纹星袍，周身星力波动明显强于同龄人。',
    personality: '骄傲自负，实力至上主义者。但并非纯粹的恶人，有自己的底线和准则。',
    background: '赵家嫡长子，星辰大陆四大家族之一的继承人。自幼被视为天才中的天才。',
    motivation: '证明赵家是最强家族，追寻至高星力。对林昊的态度从鄙视逐渐转变为忌惮。',
    abilities: '金系星辰之力（聚星境）；赵家秘传：黄金星甲。',
    catchphrase: '这个世界，实力就是规则。',
    growth_arc: [
      { id: 'ga1', chapter_range: '4-5', description: '在学院碾压众人，与林昊结怨', milestone: '登场' },
      { id: 'ga2', chapter_range: '6-7', description: '与林昊多次交手，逐渐正视对方', milestone: '转变' },
      { id: 'ga3', chapter_range: '8', description: '在大敌面前选择联手', milestone: '联手' },
    ],
    relationships: [
      { target_id: 'char-1', target_name: '林昊', type: '对手', description: '从鄙夷到正视的宿敌' },
      { target_id: 'char-2', target_name: '苏瑶', type: '追求', description: '对苏瑶有好感，但被婉拒' },
    ],
    created_at: '2025-01-17T10:00:00Z',
    updated_at: '2025-06-18T14:30:00Z',
  },
  {
    id: 'char-4',
    book_id: 'book-1',
    name: '林老',
    role: '导师',
    tag: '隐世强者',
    avatar_color: '#333333',
    portrait: '七旬老者，须发皆白，面容慈祥。看似普通的落星镇老中医，实则深不可测。',
    personality: '慈祥温和，说话总是半遮半掩。对林昊严格要求但充满关爱。隐藏着重大秘密。',
    background: '真实身份是上一代星辰至尊，因挚友之死隐居落星镇。守护着林昊血脉的秘密。',
    motivation: '守护林昊直到他能够独立，完成对故人的承诺。',
    abilities: '星辰至尊（封印状态）；医术高超；教授林昊基础星力修炼。',
    catchphrase: '孩子，真正的强者，不是从不倒下，而是倒下后还能站起来。',
    growth_arc: [
      { id: 'ga1', chapter_range: '1-2', description: '慈祥的爷爷，教导林昊做人道理', milestone: '守护' },
      { id: 'ga2', chapter_range: '3', description: '为保护林昊暴露实力，揭示身份', milestone: '揭示' },
    ],
    relationships: [
      { target_id: 'char-1', target_name: '林昊', type: '亲情', description: '祖孙情深，实为守护者' },
    ],
    created_at: '2025-01-18T10:00:00Z',
    updated_at: '2025-06-15T14:30:00Z',
  },
  // 量子深渊角色
  {
    id: 'char-5',
    book_id: 'book-2',
    name: '陈默',
    role: '主角',
    tag: '量子物理学家',
    avatar_color: '#999999',
    portrait: '三十五岁男性，消瘦的面庞上架着一副旧式眼镜。眼神中透着学者特有的专注与偏执。',
    personality: '极度理性，说话简洁精准。对未知充满狂热好奇。在社交场合显得笨拙，但在学术讨论中锋芒毕露。',
    background: 'MIT量子物理博士，回国后主导"深渊计划"。三年前妻子在一次实验中失踪，他怀疑与量子维度有关。',
    motivation: '揭开量子维度的秘密，寻找妻子的下落。',
    abilities: '量子物理天才；擅长量子场方程求解；发明了"量子锚"装置。',
    catchphrase: '数据不会说谎，但解读数据的人会。',
    growth_arc: [
      { id: 'ga1', chapter_range: '1-2', description: '带队进入量子深渊，发现异常', milestone: '启程' },
      { id: 'ga2', chapter_range: '3-4', description: '面对认知崩塌，重新理解现实', milestone: '崩塌' },
      { id: 'ga3', chapter_range: '5', description: '做出终极抉择', milestone: '抉择' },
    ],
    relationships: [
      { target_id: 'char-6', target_name: '叶澜', type: '信任', description: '探险队搭档，暗中互有好感' },
      { target_id: 'char-7', target_name: 'K-7', type: '探索', description: '量子文明的关键存在' },
    ],
    created_at: '2025-03-01T10:00:00Z',
    updated_at: '2025-06-18T09:15:00Z',
  },
  {
    id: 'char-6',
    book_id: 'book-2',
    name: '叶澜',
    role: '女主',
    tag: '特种兵指挥官',
    avatar_color: '#aaaaaa',
    portrait: '三十岁女性，短发干练，身材矫健。左脸有一道淡淡的疤痕，是某次任务留下的勋章。',
    personality: '冷静果决，行动力极强。表面严厉但关心队员。对陈默的疯狂想法既无奈又敬佩。',
    background: '特种部队"影子组"前指挥官，被选中领导深渊探险的安保工作。',
    motivation: '保护队员安全完成任务。深层动机是证明自己不只是"执行命令的机器"。',
    abilities: '顶级格斗与射击能力；战术指挥专家；量子抗性训练。',
    catchphrase: '任务优先，但每个人的命都不能放弃。',
    growth_arc: [
      { id: 'ga1', chapter_range: '1-2', description: '冷静指挥，与陈默产生理念冲突', milestone: '出征' },
      { id: 'ga2', chapter_range: '3-4', description: '在绝境中展现人性光辉', milestone: '蜕变' },
      { id: 'ga3', chapter_range: '5', description: '与陈默联手面对终极挑战', milestone: '联手' },
    ],
    relationships: [
      { target_id: 'char-5', target_name: '陈默', type: '信任', description: '从冲突到信任的搭档' },
    ],
    created_at: '2025-03-02T10:00:00Z',
    updated_at: '2025-06-17T09:15:00Z',
  },
  {
    id: 'char-7',
    book_id: 'book-2',
    name: 'K-7',
    role: '关键NPC',
    tag: '量子生命体',
    avatar_color: '#555555',
    portrait: '没有固定形态，表现为一团不断变化的光量子云。与人类交流时会凝聚出近似人形的轮廓。',
    personality: '好奇心旺盛，对人类的情感和行为模式着迷。说话方式独特，常用量子比喻。',
    background: '量子维度中的智慧生命，是量子文明最后的守望者。已经存在了相当于人类时间尺度数十亿年。',
    motivation: '寻找能与量子维度共存的方法，避免两个维度的相互毁灭。',
    abilities: '操控量子态；预知概率线；在量子维度内近乎全知。',
    catchphrase: '你们称之为"不确定性"的东西，在我们看来，是无限可能。',
    growth_arc: [
      { id: 'ga1', chapter_range: '2-3', description: '首次接触，试探与沟通', milestone: '接触' },
      { id: 'ga2', chapter_range: '4-5', description: '建立信任，提供关键帮助', milestone: '结盟' },
    ],
    relationships: [
      { target_id: 'char-5', target_name: '陈默', type: '探索', description: '相互好奇的跨维度交流' },
    ],
    created_at: '2025-03-03T10:00:00Z',
    updated_at: '2025-06-16T09:15:00Z',
  },
]

export const mockChapters: Chapter[] = [
  {
    id: 'ch-1', chapter_id: 'ch-1', chapter_number: 1, volume: '第一卷·落星镇',
    title: '废脉少年', word_count: 580, status: 'final', target_words: 3000,
    summary: '林昊在落星镇的日常生活，展现他作为"废脉少年"遭受的冷眼，以及在爷爷教导下的坚韧成长。',
    content: `# 第一章 废脉少年\n\n落星镇的黄昏总是来得特别早。\n\n当最后一缕夕阳从镇东头那棵老槐树的枝桠间滑落时，整个小镇便沉浸在一片昏黄的暮色之中。街边的铺子陆续亮起了油灯，偶尔传来几声犬吠和孩童的嬉闹。\n\n林昊蹲在镇口的石桥上，手里攥着一根柳枝，无意识地在河面上画着什么。\n\n河水映出他的倒影——一个十七岁的少年，身形清瘦，黑发被晚风吹得有些凌乱。唯有那双眼睛，在暮色中依然明亮得不像话，像是藏着两颗不肯熄灭的星子。\n\n"又在发呆？"\n\n一个苍老但不失中气声音从身后传来。林昊不用回头就知道是谁。\n\n"爷爷。"他站起身，拍了拍裤子上的灰。\n\n林老拄着拐杖，慢悠悠地走到桥栏边，眯着眼看了看天边的晚霞。"明天就是星辰学院的招生了。"\n\n林昊的手指不自觉地收紧，柳枝"啪"地断成了两截。\n\n"不去也行。"林老似乎没注意到他的异样，慢吞吞地说，"镇上的猎户老张说要收个徒弟——"\n\n"我去。"\n\n林老看了他一眼，嘴角微微弯起一个弧度，又很快恢复了平淡的表情。\n\n"那就早点睡。"\n\n……\n\n夜深了，林昊躺在阁楼的旧木床上，左臂上那道星形胎记隐隐发出微光。\n\n他不知道的是，千里之外的星辰学院，一块沉寂千年的古碑突然震动了一下。碑面上浮现出几个若隐若现的古字，随即又消失不见。\n\n守碑的老者猛然睁开了浑浊的双眼。\n\n"终于……出现了吗？"\n`,
    updated_at: '2025-05-10T16:00:00Z',
  },
  {
    id: 'ch-2', chapter_id: 'ch-2', chapter_number: 2, volume: '第一卷·落星镇',
    title: '星纹觉醒', word_count: 0, status: 'final', target_words: 3000,
    summary: '林昊在离家前夕遭遇山匪，危急时刻星纹胎记觉醒，释放出惊人的星力波动。',
    content: '',
    updated_at: '2025-05-15T16:00:00Z',
  },
  {
    id: 'ch-3', chapter_id: 'ch-3', chapter_number: 3, volume: '第一卷·落星镇',
    title: '离乡之路', word_count: 0, status: 'reviewing', target_words: 3000,
    summary: '林昊告别爷爷踏上前往星辰学院的路途，途中初遇神秘旅人。',
    updated_at: '2025-06-01T16:00:00Z',
  },
  {
    id: 'ch-4', chapter_id: 'ch-4', chapter_number: 4, volume: '第二卷·星辰学院',
    title: '天才汇聚', word_count: 0, status: 'writing', target_words: 3500,
    summary: '林昊进入星辰学院，见识到各路天才，感受到巨大的差距和压力。',
    updated_at: '2025-06-10T16:00:00Z',
  },
  {
    id: 'ch-5', chapter_id: 'ch-5', chapter_number: 5, volume: '第二卷·星辰学院',
    title: '初次交锋', word_count: 0, status: 'draft', target_words: 3500,
    summary: '在学院考核中，林昊与赵无极发生正面冲突，以弱胜强震惊全场。',
    updated_at: '2025-06-15T16:00:00Z',
  },
  {
    id: 'ch-6', chapter_id: 'ch-6', chapter_number: 6, volume: '第二卷·星辰学院',
    title: '暗流涌动', word_count: 0, status: 'draft', target_words: 3000,
    summary: '学院中开始出现针对林昊的阴谋，苏瑶察觉异常暗中提醒。',
    updated_at: '2025-06-18T16:00:00Z',
  },
  {
    id: 'ch-7', chapter_id: 'ch-7', chapter_number: 7, volume: '第二卷·星辰学院',
    title: '身世之谜', word_count: 0, status: 'draft', target_words: 3500,
    summary: '林昊偶然发现父母留下的线索，引出更大的世界观。',
    updated_at: '2025-06-19T16:00:00Z',
  },
  {
    id: 'ch-8', chapter_id: 'ch-8', chapter_number: 8, volume: '第二卷·星辰学院',
    title: '风起云涌', word_count: 0, status: 'draft', target_words: 4000,
    summary: '第一卷结尾，多方势力汇聚，林昊踏上新的征程。',
    updated_at: '2025-06-20T16:00:00Z',
  },
  // 量子深渊章节
  {
    id: 'ch-9', chapter_id: 'ch-9', chapter_number: 1, volume: '第一卷·深渊入口',
    title: '深渊计划', word_count: 0, status: 'final', target_words: 3000,
    summary: '陈默介绍量子深渊计划的背景，探险队组建完成。',
    updated_at: '2025-05-20T16:00:00Z',
  },
  {
    id: 'ch-10', chapter_id: 'ch-10', chapter_number: 2, volume: '第一卷·深渊入口',
    title: '第一道门', word_count: 0, status: 'reviewing', target_words: 3000,
    summary: '探险队成功进入量子维度，发现物理法则完全不同。',
    updated_at: '2025-06-05T16:00:00Z',
  },
  {
    id: 'ch-11', chapter_id: 'ch-11', chapter_number: 3, volume: '第一卷·深渊入口',
    title: '量子幽灵', word_count: 0, status: 'writing', target_words: 3500,
    summary: '首次遭遇量子生命体K-7，双方紧张试探。',
    updated_at: '2025-06-10T16:00:00Z',
  },
  {
    id: 'ch-12', chapter_id: 'ch-12', chapter_number: 4, volume: '第二卷·维度深处',
    title: '认知崩塌', word_count: 0, status: 'draft', target_words: 3500,
    summary: '陈默发现自己的物理理论在这里完全失效，精神濒临崩溃。',
    updated_at: '2025-06-15T16:00:00Z',
  },
  {
    id: 'ch-13', chapter_id: 'ch-13', chapter_number: 5, volume: '第二卷·维度深处',
    title: '终极抉择', word_count: 0, status: 'draft', target_words: 4000,
    summary: '两个维度面临碰撞危机，陈默必须做出牺牲性选择。',
    updated_at: '2025-06-18T16:00:00Z',
  },
]

export const mockHooks: Hook[] = [
  { id: 'hook-1', book_id: 'book-1', title: '林昊的血脉之谜', description: '左臂星纹胎记的真正含义，与远古星辰至尊的血脉关联', status: 'activated', planted_chapter: 1, target_chapter: 7, priority: 'high', created_at: '2025-04-01T10:00:00Z', updated_at: '2025-06-15T10:00:00Z' },
  { id: 'hook-2', book_id: 'book-1', title: '父母失踪真相', description: '林昊父母为何在五年前突然消失，与古碑的关联', status: 'advancing', planted_chapter: 1, target_chapter: 8, priority: 'high', created_at: '2025-04-01T10:00:00Z', updated_at: '2025-06-18T10:00:00Z' },
  { id: 'hook-3', book_id: 'book-1', title: '古碑震动', description: '星辰学院千年古碑在林昊觉醒时震动，守碑老者的身份', status: 'planted', planted_chapter: 1, target_chapter: 5, priority: 'medium', created_at: '2025-04-01T10:00:00Z', updated_at: '2025-04-01T10:00:00Z' },
  { id: 'hook-4', book_id: 'book-1', title: '林老的真实身份', description: '爷爷林老曾是上一代星辰至尊，因何隐居', status: 'advancing', planted_chapter: 2, target_chapter: 6, priority: 'high', created_at: '2025-04-05T10:00:00Z', updated_at: '2025-06-10T10:00:00Z' },
  { id: 'hook-5', book_id: 'book-1', title: '苏瑶的银铃', description: '苏瑶腰间银铃的来历，具有预知危险的能力', status: 'planted', planted_chapter: 3, target_chapter: 6, priority: 'medium', created_at: '2025-04-10T10:00:00Z', updated_at: '2025-04-10T10:00:00Z' },
  { id: 'hook-6', book_id: 'book-2', title: '陈默妻子的失踪', description: '三年前实验中失踪的妻子，可能与量子维度有关', status: 'activated', planted_chapter: 1, target_chapter: 5, priority: 'high', created_at: '2025-04-01T10:00:00Z', updated_at: '2025-06-10T10:00:00Z' },
  { id: 'hook-7', book_id: 'book-2', title: '量子锚的异常', description: '量子锚设备读数异常，暗示维度边界正在变薄', status: 'planted', planted_chapter: 2, target_chapter: 4, priority: 'medium', created_at: '2025-04-05T10:00:00Z', updated_at: '2025-04-05T10:00:00Z' },
  { id: 'hook-8', book_id: 'book-2', title: 'K-7的真实目的', description: '量子生命体K-7帮助人类的真实动机是否纯粹', status: 'planted', planted_chapter: 3, target_chapter: 5, priority: 'high', created_at: '2025-04-10T10:00:00Z', updated_at: '2025-04-10T10:00:00Z' },
]

export const mockTimelineEvents: TimelineEvent[] = [
  { id: 'tl-1', book_id: 'book-1', title: '远古诸神之战', description: '远古星辰至尊们为争夺至高星力爆发大战，导致诸神陨落', time_point: '远古纪元', chapter_ref: 0, category: '历史', created_at: '2025-01-15T10:00:00Z' },
  { id: 'tl-2', book_id: 'book-1', title: '林昊出生', description: '林昊出生于落星镇，父母为保护他封印其血脉', time_point: '17年前', chapter_ref: 0, category: '人物', created_at: '2025-01-15T10:00:00Z' },
  { id: 'tl-3', book_id: 'book-1', title: '父母失踪', description: '林昊五岁时，父母在一夜之间神秘消失', time_point: '12年前', chapter_ref: 0, category: '事件', created_at: '2025-01-15T10:00:00Z' },
  { id: 'tl-4', book_id: 'book-1', title: '星纹觉醒', description: '林昊在落星镇遭遇山匪时，左臂星纹首次发光', time_point: '故事开始', chapter_ref: 2, category: '事件', created_at: '2025-04-05T10:00:00Z' },
  { id: 'tl-5', book_id: 'book-1', title: '进入星辰学院', description: '林昊通过考核进入星辰学院', time_point: '第一卷·第3章', chapter_ref: 3, category: '事件', created_at: '2025-04-10T10:00:00Z' },
  { id: 'tl-6', book_id: 'book-1', title: '首次击败赵无极', description: '学院考核中林昊以弱胜强', time_point: '第二卷·第5章', chapter_ref: 5, category: '战斗', created_at: '2025-04-20T10:00:00Z' },
  { id: 'tl-7', book_id: 'book-2', title: '深渊计划启动', description: '量子维度探测计划正式启动', time_point: '2187年3月', chapter_ref: 1, category: '事件', created_at: '2025-03-01T10:00:00Z' },
  { id: 'tl-8', book_id: 'book-2', title: '首次接触K-7', description: '探险队在量子维度深处遭遇量子生命体', time_point: '2187年4月', chapter_ref: 3, category: '事件', created_at: '2025-04-10T10:00:00Z' },
]

export const mockWorldBuilding: WorldBuilding = {
  id: 'world-1',
  book_id: 'book-1',
  geography: `# 星辰大陆地理\n\n## 总体格局\n星辰大陆东西横跨万里，分为五大区域：\n\n- **东域**：星辰学院所在，灵气浓郁，是修炼圣地\n- **西域**：荒芜沙漠，传说埋藏着远古遗迹\n- **南域**：万兽山脉，妖兽横行，资源丰富\n- **北域**：冰封之地，隐藏着上古秘辛\n- **中域**：四大家族领地，权势中心\n\n## 落星镇\n位于东域边缘的小镇，人口约三千。因传说有星辰陨落此地而得名。镇后的落星山中有一处隐秘的远古遗迹。`,
  factions: `# 势力分布\n\n## 星辰学院\n大陆最强修炼学府，传承千年。院长苏天河实力深不可测。\n\n## 四大家族\n- **赵家**：中域霸主，金系星力传承\n- **王家**：南域掌控者，擅长丹药\n- **李家**：东域望族，精通阵法\n- **孙家**：北域守护者，冰系星力\n\n## 暗势力\n传说中"星陨阁"在暗中收集远古遗物，目的不明。`,
  power_system: `# 力量体系：星辰之力\n\n## 修炼境界\n1. **引星境**：感应星辰之力，引入体内（林昊初期）\n2. **聚星境**：星力凝聚成型，可外放攻击（赵无极等级）\n3. **化星境**：星力化形，形成星铠星兵\n4. **星王境**：星力自成领域\n5. **星皇境**：操控天地星力\n6. **星帝境**：传说中境界，远古诸神等级\n7. **星辰至尊**：超越星帝，万古唯一（林老真实等级）\n\n## 特殊能力\n- **星纹觉醒**：血脉中蕴含的远古力量\n- **星力吞噬**：可吸收他人星力为己用\n- **星辰共鸣**：多人心意相通，星力叠加`,
  history: `# 大陆历史\n\n## 远古纪元\n诸神争霸时代，七位星辰至尊为争夺"至高星核"爆发旷世大战。最终诸神同归于尽，星核碎裂散落大陆各处。\n\n## 千年前\n星辰学院第一任院长发现古碑，开创修炼体系传承至今。\n\n## 百年前\n四大家族联手击退域外邪魔，奠定当今格局。\n\n## 近事\n- 17年前：林昊出生\n- 12年前：林昊父母失踪\n- 故事开始：林昊觉醒星纹`,
  social_rules: `# 社会规则\n\n## 修炼者等级制度\n- 修炼者享有极高社会地位\n- 学院弟子可免除赋税\n- 家族势力决定资源分配\n\n## 禁忌\n- 禁止修炼吞噬类功法（被星陨阁暗中使用）\n- 禁止私入远古遗迹\n- 禁止对凡人使用星力\n\n## 货币\n星辰币，以蕴含星力的矿石铸造。1星辰币约等于凡人一年收入。`,
  factions_graph: [
    { id: 'fg-1', name: '星辰学院', description: '大陆最强学府', relations: [{ target: '赵家', type: '合作' }, { target: '星陨阁', type: '暗中对抗' }] },
    { id: 'fg-2', name: '赵家', description: '中域霸主', relations: [{ target: '星辰学院', type: '合作' }, { target: '王家', type: '竞争' }] },
    { id: 'fg-3', name: '星陨阁', description: '神秘暗势力', relations: [{ target: '星辰学院', type: '暗中对抗' }, { target: '远古遗迹', type: '探索' }] },
    { id: 'fg-4', name: '王家', description: '南域望族', relations: [{ target: '赵家', type: '竞争' }, { target: '李家', type: '联盟' }] },
  ],
  timeline_events: mockTimelineEvents.filter(e => e.book_id === 'book-1'),
}

export const mockOutline: OutlineNode[] = [
  {
    id: 'vol-1', title: '第一卷·落星镇', type: 'volume', children: [
      { id: 'ch-o-1', title: '废脉少年', type: 'chapter', chapter_number: 1, summary: '林昊在落星镇的生活，展现"废脉"身份带来的屈辱和坚韧', beat_points: [{ id: 'bp-1', label: '日常', description: '展示林昊的日常与内心', act: 1 }, { id: 'bp-2', label: '激励事件', description: '学院招生消息传来', act: 1 }] },
      { id: 'ch-o-2', title: '星纹觉醒', type: 'chapter', chapter_number: 2, summary: '离乡前遭遇山匪，星纹觉醒释放星力', beat_points: [{ id: 'bp-3', label: '危机', description: '山匪袭击', act: 1 }, { id: 'bp-4', label: '转折', description: '星纹觉醒', act: 1 }] },
      { id: 'ch-o-3', title: '离乡之路', type: 'chapter', chapter_number: 3, summary: '告别爷爷，踏上前往学院之路', beat_points: [{ id: 'bp-5', label: '离别', description: '与爷爷告别', act: 1 }, { id: 'bp-6', label: '启程', description: '踏上未知旅途', act: 1 }] },
    ]
  },
  {
    id: 'vol-2', title: '第二卷·星辰学院', type: 'volume', children: [
      { id: 'ch-o-4', title: '天才汇聚', type: 'chapter', chapter_number: 4, summary: '进入学院，见识各路天才', beat_points: [{ id: 'bp-7', label: '新世界', description: '展现学院的恢弘', act: 2 }, { id: 'bp-8', label: '压力', description: '感受到差距', act: 2 }] },
      { id: 'ch-o-5', title: '初次交锋', type: 'chapter', chapter_number: 5, summary: '考核中与赵无极正面冲突', beat_points: [{ id: 'bp-9', label: '冲突', description: '赵无极挑衅', act: 2 }, { id: 'bp-10', label: '逆转', description: '以弱胜强', act: 2 }] },
      { id: 'ch-o-6', title: '暗流涌动', type: 'chapter', chapter_number: 6, summary: '阴谋浮现，苏瑶暗中提醒', beat_points: [{ id: 'bp-11', label: '危机', description: '发现阴谋', act: 2 }, { id: 'bp-12', label: '线索', description: '苏瑶提供信息', act: 2 }] },
      { id: 'ch-o-7', title: '身世之谜', type: 'chapter', chapter_number: 7, summary: '发现父母留下的线索', beat_points: [{ id: 'bp-13', label: '发现', description: '找到父母遗物', act: 3 }, { id: 'bp-14', label: '真相', description: '揭开部分真相', act: 3 }] },
      { id: 'ch-o-8', title: '风起云涌', type: 'chapter', chapter_number: 8, summary: '多方势力汇聚，踏上新征程', beat_points: [{ id: 'bp-15', label: '汇聚', description: '各方势力登场', act: 3 }, { id: 'bp-16', label: '出发', description: '踏上更大舞台', act: 3 }] },
    ]
  },
]

export const mockBeatPoints: BeatPoint[] = [
  { id: 'bp-1', label: '日常展现', description: '林昊在落星镇的日常生活，被嘲笑的场景', act: 1 },
  { id: 'bp-2', label: '激励事件', description: '星辰学院招生消息传来', act: 1 },
  { id: 'bp-3', label: '第一幕高潮', description: '星纹觉醒，击退山匪', act: 1 },
  { id: 'bp-4', label: '进入新世界', description: '踏入星辰学院', act: 2 },
  { id: 'bp-5', label: '试炼与成长', description: '学院考核中不断突破', act: 2 },
  { id: 'bp-6', label: '中点逆转', description: '以弱胜强击败赵无极', act: 2 },
  { id: 'bp-7', label: '黑暗时刻', description: '发现阴谋，陷入困境', act: 2 },
  { id: 'bp-8', label: '真相揭示', description: '发现父母线索', act: 3 },
  { id: 'bp-9', label: '最终决战', description: '多方势力对决', act: 3 },
  { id: 'bp-10', label: '新的征程', description: '踏上更大的舞台', act: 3 },
]

export const mockWorkflow: WorkflowState = {
  workflow_id: 'wf-1',
  workflow_type: 'chapter-production',
  book_id: 'book-1',
  status: 'running',
  current_node: 'humanize',
  loop_count: 0,
  created_at: '2025-06-20T14:00:00Z',
  updated_at: '2025-06-20T14:30:00Z',
  error: null,
  nodes: {
    plan: { node_id: 'plan', status: 'success', summary: '大纲已生成', output_files: [], metadata: {}, error: null },
    compose: { node_id: 'compose', status: 'success', summary: '上下文已组装', output_files: [], metadata: {}, error: null },
    write: { node_id: 'write', status: 'success', summary: '生成3200字初稿', output_files: [], metadata: {}, error: null },
    audit: { node_id: 'audit', status: 'success', summary: '评分82分', output_files: [], metadata: {}, error: null },
    humanize: { node_id: 'humanize', status: 'running', summary: '润色中', output_files: [], metadata: {}, error: null },
    done: { node_id: 'done', status: 'pending', summary: '', output_files: [], metadata: {}, error: null },
  },
  pending_approval: null,
}

export const mockQualityScore: QualityScore = {
  character_consistency: 85,
  plot_logic: 78,
  language_natural: 82,
  pacing: 70,
  ai_detection: 65,
}

export const mockTokenBudget: TokenBudget = {
  total: 8000,
  used: 5200,
  breakdown: [
    { label: '前文摘要', tokens: 1200, color: '#ffffff' },
    { label: '角色信息', tokens: 800, color: '#cccccc' },
    { label: '世界规则', tokens: 600, color: '#999999' },
    { label: '本章大纲', tokens: 400, color: '#777777' },
    { label: '伏笔追踪', tokens: 300, color: '#555555' },
    { label: '预留写作', tokens: 1900, color: '#333333' },
    { label: '空闲', tokens: 2800, color: '#1a1a1a' },
  ],
}

export const mockReviewReport: ReviewReport = {
  id: 'review-1',
  chapter_id: 'ch-1',
  scores: mockQualityScore,
  overall_score: 76,
  issues: [
    { type: '人物一致', severity: 'medium', location: '第3段', description: '林昊对话风格略显成熟，与其17岁年龄不太匹配', suggestion: '可适当增加少年感的口语表达' },
    { type: '情节逻辑', severity: 'low', location: '第7段', description: '古碑震动的时间点与林昊觉醒的同步性未做铺垫', suggestion: '可加入一些暗示性的描写' },
    { type: 'AI味检测', severity: 'high', location: '第2段', description: '"像是藏着两颗不肯熄灭的星子"修辞略显刻意', suggestion: '可改为更朴实的描写方式' },
  ],
  suggestions: [
    '开篇环境描写可以适当精简，加快进入人物',
    '林老的形象可以通过具体动作而非旁白来塑造',
    '章节结尾的悬念设置较好，建议保持',
  ],
  created_at: '2025-05-10T16:00:00Z',
}

export const mockRecentActivities: RecentActivity[] = [
  { id: 'act-1', type: 'generate', chapter_title: '天才汇聚', book_title: '星辰大陆', timestamp: '2025-06-20T14:30:00Z', status: 'success' },
  { id: 'act-2', type: 'review', chapter_title: '离乡之路', book_title: '星辰大陆', timestamp: '2025-06-19T16:00:00Z', status: 'success' },
  { id: 'act-3', type: 'polish', chapter_title: '第一道门', book_title: '量子深渊', timestamp: '2025-06-18T09:15:00Z', status: 'success' },
  { id: 'act-4', type: 'generate', chapter_title: '量子幽灵', book_title: '量子深渊', timestamp: '2025-06-17T14:00:00Z', status: 'pending' },
  { id: 'act-5', type: 'review', chapter_title: '废脉少年', book_title: '星辰大陆', timestamp: '2025-05-10T16:00:00Z', status: 'success' },
]
