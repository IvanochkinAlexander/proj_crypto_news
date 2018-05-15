import newspaper
import pandas as pd
import datetime
from bs4 import BeautifulSoup
import re
import time
import requests
from newspaper import Article
import telegram
import nltk
from nltk.util import ngrams
from string import punctuation
from nltk.tokenize import WhitespaceTokenizer
from pymorphy2 import MorphAnalyzer
from nltk.tokenize import sent_tokenize
from nltk.tokenize import word_tokenize
from bs4 import BeautifulSoup as bs
from nltk.corpus import stopwords
from gensim import corpora, models, similarities
from gensim.models import doc2vec
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import random
import newsapi
import urllib
from nltk import WordNetLemmatizer

# exclude = set(punctuation + u'0123456789[]—«»–')


"""Script sends new about crypto currency to Telegram channel"""


def get_links (t, l):

    """Parsing links from duckduckgo.com"""

    links=[]
    links_alfa = []
    links_df = pd.DataFrame()

    print (l,t)
    t= urllib.request.quote(t.encode('utf8'))
    browser.set_window_size(1120, 550)
    browser.get("https://duckduckgo.com/?q={}".format(t)+ "&ar=news&ia=news&kl={}".format(l))
    browser.find_element_by_id('search_form_input').send_keys(t)
    # NEXT_BUTTON_XPATH = '//*[@id="links_wrapper"]/div[2]/div/a'
    NEXT_BUTTON_XPATH ='//*[@id="links_wrapper"]/div[1]/div[2]/div/a'
    button = browser.find_element_by_xpath(NEXT_BUTTON_XPATH)
    button.click()
    page = browser.page_source
    soup = BeautifulSoup(page, 'lxml')
    print (browser.current_url)
    for item in soup.find_all('a', attrs={'class' : 'result__a'}):
        links.append(str(item).split('href="')[1].split('"')[0])
    time.sleep(random.choice(range(5,13)))
    links_df = pd.DataFrame(links)
    links_df = links_df.rename(columns={0:'url'})
    links_df = links_df[:17]
    return links_df

def parse_links_ru(links_df):

    """Get Russian text data from target web sites"""

    texts = []
    links = []
    text_df = pd.DataFrame()
    for i in links_df['url']:
        try:
            a = Article(i, language='ru')
            a.download()
            a.parse()
            texts.append(a.text)
            links.append(i)
        except:
            pass
    temp_df = pd.DataFrame(texts, links)
    text_df = pd.concat([text_df, temp_df])
    text_df = text_df.reset_index()
    text_df.columns = ('link', 'full_text')
    return text_df

def parse_links(links_df):

    """Get English text data from target web sites"""

    texts = []
    links = []
    text_df = pd.DataFrame()

    for i in links_df['url']:
        try:
            a = Article(i, language='en')
            a.download()
            a.parse()
            texts.append(a.text)
            links.append(i)
        except:
            pass
    temp_df = pd.DataFrame(texts, links)
    text_df = pd.concat([text_df, temp_df])
    text_df = text_df.reset_index()
    text_df.columns = ('link', 'full_text')
    return text_df


def No_with_word(token_text):

    """Concating NO with words"""

    tmp=''
    for i,word in enumerate(token_text):
        if word==u'не':
            tmp+=("_".join(token_text[i:i+2]))
            tmp+= ' '
        else:
            if token_text[i-1]!=u'не':
                tmp+=word
                tmp+=' '
    return tmp


def wrk_words_wt_no(sent):

    """Making lemmatisation for Russian and English text"""

    words=word_tokenize(sent.lower())
    lemmatizer = WordNetLemmatizer()
    try:
        arr=[]
        for i in range(len(words)):
            arr.append(morph.parse(words[i])[0].normal_form)
        arr2 = []
        for i in arr:
            arr2.append(lemmatizer.lemmatize(i, pos='v'))
        arr3 = []
        for i in arr2:
            arr3.append(lemmatizer.lemmatize(i, pos='n'))
        arr4 = []
        for i in arr3:
            arr4.append(lemmatizer.lemmatize(i, pos='a'))
        words1=[w for w in arr4 if w not in russian_stops]
        words1=[w for w in arr4 if w not in english_stops]
        words1=No_with_word(words1)
        return words1
    except TypeError:
        pass

def find_keywords (text_df, links_df):

    """Find keywords to filter approppriate links"""

    russian_stops = stopwords.words('russian')
    english_stops = stopwords.words('english')
    morph = MorphAnalyzer()
    collection = [wrk_words_wt_no(text) for text in text_df ['full_text']]
    all_text_keywords = []
    collection_df = pd.DataFrame(collection)
    collection_df = collection_df.rename(columns={0:'text'})
    for text in collection:
        token_text = word_tokenize(text)
        token_text_2 = [" ".join(value) for value in list(ngrams(token_text,2))]
        token_text_3 = [" ".join(value) for value in list(ngrams(token_text,3))]
        token_text_4 = [" ".join(value) for value in list(ngrams(token_text,4))]
        text_keywords = ''
        for word in to_search:
            if (word in token_text) | (word in token_text_2) | (word in token_text_3) | (word in token_text_4):
                text_keywords+=word
                text_keywords+=' '
        all_text_keywords.append(text_keywords)
    concated_df = pd.concat([links_df.reset_index(drop=True), text_df, pd.DataFrame(all_text_keywords), collection_df], axis=1)
    concated_df = concated_df.drop_duplicates(subset='link', keep='first').reset_index(drop=True)
    return concated_df

def to_exclude_text(concated_df):
    not_to_search = ['лига','баскетобол', 'хоккей', 'sport', 'матч', 'турнир', 'чемпионат', 'тренер', 'спортивный']
    to_exclude = []
    num_list = []
    concated_df['text'] = concated_df['text'].fillna('пусто')
    for num, i in enumerate(concated_df['text']):
        for word in not_to_search:
            if word in i:
                to_exclude.append(word)
                num_list.append(num)
            else:
                to_exclude.append(0)
                num_list.append(num)
    temp_exclude = pd.concat([pd.DataFrame(num_list), pd.DataFrame(to_exclude)], axis=1)
    temp_exclude.columns = ('num', 'tag')
    true_index = temp_exclude[temp_exclude['tag']==0]['num'].unique()
    concated_df = concated_df.iloc[true_index]
    return concated_df, temp_exclude

def send_to_telegram(i, m, c):

    """Send appropriate links to telegram channel"""

    bot = telegram.Bot(token='')
    chat_id = ''
    bot.send_message(chat_id=chat_id, text=\
                     'Country:' + '\n' + '{}'.format(c) + "\n" + \
                     'Tags:' + "\n"+ '{}'.format(i) + "\n" + \
                     '{}'.format(m))
    time.sleep(25)

def review_to_wordlist(review):

    """Convert collection to wordlist"""

    words = review.lower().split()
    words = [w for w in words]
    return(words)

def find_duplicates (df_text):

    """
    Count cosine similarity on TF-IDF vectors
    """
    sims_df = pd.DataFrame()
    try:
        dictionary = corpora.Dictionary(df_text)
        corpus = [dictionary.doc2bow(t) for t in df_text]
        tfidf = models.TfidfModel(corpus)
        corpus_tfidf = tfidf[corpus]
        index = similarities.MatrixSimilarity(tfidf[corpus])
        sims = index[corpus_tfidf]
        sims_df = pd.DataFrame(sims)
        for i in range(len(df_text)):
            sims_df.iloc[i,i] = -1
        cols = sims_df.columns
        sims_df['max_text'] = sims_df.apply(lambda x: sims_df.columns[x == x.max()][0], axis=1)
        sims_df['max_text_proba'] = sims_df[cols].max(axis=1)
        return sims_df[['max_text', 'max_text_proba']]
    except:
        return sims_df
    # pass

def del_interntal_duplicates(concated_cut):

    """
    Delete duplicates using cosine similarity on TF-IDF
    vectors not to allow send similiar news about banks

    """
    concated_sims = pd.DataFrame()
    try:
        sims = find_duplicates (concated_cut['text'].apply(review_to_wordlist))
        concated_sims = pd.concat([concated_cut.reset_index(drop=True), sims], axis=1)
        more_df = concated_sims[concated_sims['max_text_proba']>=0.6]
        less_df = concated_sims[concated_sims['max_text_proba']<0.6]
        more_df = more_df.drop_duplicates(subset='max_text_proba', keep='first')
        concated_sims  = pd.concat([less_df, more_df])
        del concated_sims['max_text_proba']
        del concated_sims['max_text']
        return concated_sims
    except:
        return concated_sims

# to_search = [
#      'новый продукт',
#      'новые условия',
#      'впервые',
#      'первые на рынок',
#      'банк представить',
#      'выводить на рынок',
#      'любое отделение',
#      'любой сотрудник',
#      'любой клиент',
#      'без очереди',
#      'любой специалист',
#      'без ожидание',
#      'любой время',
#      'один документ',
#      'два документа',
#      'новый технология',
#      'новый процесс',
#      'появление возможность',
#      'становиться быстрее',
#      'новый возможность',
#      'инновация',
#      'сокращение',
#      'инновационный',
#      'начинать',
#      'появиться',
#      'альфа-банк',
#      'альфабанк',
#      'альфа банк'
#     'тинькофф',
#     'сбербанк',
#     'модульбанк',
#     'газпромбанк',
#     'точка банк',
#     'втб',
#     'райффайзен',
#     'юникредит',
#     'фк открытие',
#     'бинбанк','new product',
# 'new conditions',
# 'first on the market',
# 'bank to present',
# 'bring to the market',
# 'any department',
# 'any employee',
# 'any customer',
# 'no turn',
# 'any specialist',
# 'no waiting',
# 'any time',
# 'one document',
# 'two documents',
# 'new technology',
# 'new process',
# 'get faster',
# 'faster',
# 'better',
# 'new opportunity',
# 'innovation',
# 'innovative',
# 'start up',
# 'machine learning',
# 'biometric technology',
# 'new technology',
# 'big data',
# 'robotic technology',
# 'bank of america',
# 'royal bank of canada',
# 'industrial and commercial bank of china',
# 'citibank',
# 'societe generale',
# 'standard chartered bank',
# 'sorthern trust',
# 'maybank islamic',
# 'ubs',
# 'citibank',
# 'bnp paribas',
# 'jp morgan',
# 'bank of america',
# 'ing',
# 'raiffeisen',
# 'santander',
# 'icbc',
# 'arab bank',
# 'standard bank',
# 'lead off'
# 'premier'
# 'leading-edge'
# 'breaking new ground'
# 'state-of-the-art'
# 'progressive',
# 'latest',
# 'brand-new',
# 'unique',
# 'leading',
# 'machine',
# 'robotics',
# 'hi tech',
# 'scientific',
# 'digital',
# 'artificial',
# 'intelligence'
# ]


to_search = [
'BitcoinBTC',
'EthereumETH',
'RippleXRP',
'Bitcoin CashBCH',
'LitecoinLTC',
'DashDASH',
'NEMXEM',
'BitConnectBCC',
'NEONEO',
'MoneroXMR',
'IOTAMIOTA',
'Ethereum ClassicETC',
'QtumQTUM',
'CardanoADA',
'OmiseGOOMG',
'LiskLSK',
'ZcashZEC',
'Stellar LumensXLM',
'TetherUSDT',
'WavesWAVES',
'HshareHSR',
'StratisSTRAT',
'ArkARK',
'BytecoinBCN',
'SteemSTEEM',
'EOSEOS',
'ArdorARDR',
'GolemGNT',
'TenXPAY',
'AugurREP',
'PIVXPIVX',
'FirstCoinFRST',
'KomodoKMD',
'MaidSafeCoinMAID',
'GasGAS',
'WaltonWTC',
'DecredDCR',
'MonaCoinMONA',
'SALTSALT',
'Basic Attenti BAT',
'Kyber NetworkKNC',
'MetalMTL',
'FactomFCT',
'TRONTRX',
'BitSharesBTS',
'IconomiICN',
'VeritaseumVERI',
'DigixDAODGD',
'PopulousPPT',
'Binance CoinBNB',
'GameCreditsGAME',
'Metaverse ETPETP',
'CivicCVC',
'SiacoinSC',
'DogecoinDOGE',
'Byteball BytesGBYTE',
'RegalcoinREC',
'BitcoinDarkBTCD',
'xZRX',
'BlocknetBLOCK',
'LykkeLKK',
'SyscoinSYS',
'StatusSNT',
'SingularDTVSNGLS',
'BancorBNT',
'BytomBTM',
'ATMChainATM',
'ChainLinkLINK',
'MCAPMCAP',
'DigiByteDGB',
'FunFairFUN',
'GnosisGNO',
'AeternityAE',
'VertcoinVTC',
'MonacoMCO',
'GXSharesGXS',
'NexusNXS',
'PuraPURA',
'VeChainVEN',
'BitdealBDL',
'NxtNXT',
'VergeXVG',
'SmartCashSMART',
'NeblioNEBL',
'NoLimitCoinNLC',
'BitquenceBQX',
'AragonANT',
'ParticlPART',
'ATBCoinATB',
'NAV CoinNAV',
'UbiqUBQ',
'TaaSTAAS',
'I/O CoinIOC',
'KinKIN',
'LoopringLRC',
'AdExADX',
'ZenCashZEN',
'iExec RLCRLC',
'AirSwapAST',
'MelonMLN',
'WingsWINGS',
'EdgelessEDG',
'MobileGoMGO',
'FairCoinFAIR',
'CentraCTR',
'StorjSTORJ',
'DentacoinDCN',
'SONMSNM',
'GuldenNLG',
'district xDNT',
'CloakCoinCLOAK',
'ZCoinXZC',
'EnigmaENG',
'Quantum Resis QRL',
'PeercoinPPC',
'SubstratumSUB',
'ReddCoinRDD',
'WeTrustTRST',
'AschXAS',
'Cofound itCFI',
'RiseRISE',
'ElasticXEL',
'TokenCardTKN',
'DecentralandMANA',
'EidooEDO',
'Moeda Loyalty MDA',
'XaurumXAUR',
'CompcoinCMP',
'Blackmoon CryptoBMC',
'DECENTDCT',
'AeonAEON',
'LEOcoinLEO',
'CindicatorCND',
'EtherollDICE',
'CrownCRW',
'BitBayBAY',
'EmercoinEMC',
'PillarPLR',
'Safe Exchange SAFEX',
'ViacoinVIA',
'FirstBlood ST',
'TierionTNT',
'bitqyBQ',
'SuperNETUNITY',
'SkycoinSKY',
'CoinDashCDT',
'IONION',
'CounterpartyXCP',
'The ChampCoinTCC',
'AventusAVT',
'RubycoinRBY',
'SIBCoinSIB',
'NumeraireNMR',
'KickCoinKICK',
'PayPiePPP',
'DiamondDMD',
'EverexEVX',
'adTokenADT',
'RialtoXRL',
'TriggersTRIG',
'NamecoinNMC',
'ViberateVIB',
'EinsteiniumEMC',
'PolybiusPLBT',
'Pepe CashPEPECASH',
'CredoCREDO',
'MothershipMSP',
'TransferCoinTX',
'MonethaMTH',
'UnobtaniumUNO',
'PatientoryPTOY',
'EnergycoinENRG',
'SaluSSLS',
'Santiment Net SAN',
'LBRY CreditsLBC',
'PeerplaysPPY',
'ChronobankTIME',
'Agoras TokensAGRS',
'EtherDogeEDOGE',
'E coinECN',
'PotCoinPOT',
'AgrelloDLT',
'RaiBlocksXRB',
'StoxSTX',
'MonetaryUnitMUE',
'BlackCoinBLK',
'Po etPOE',
'ExpanseEXP',
'GolosGOLOS',
'CasinoCoinCSC',
'GridCoinGRC',
'ToaCoinTOA',
'OKCashOK',
'RivetzRVT',
'ALISALIS',
'HiveHVN',
'LunyrLUN',
'OmniOMNI',
'MaecenasART',
'MysteriumMYST',
'FlorinCoinFLO',
'NexiumNXC',
'HumaniqHMQ',
'RadiumRADS',
'BitDiceCSNO',
'B CoinB',
'ShiftSHIFT',
'BurstBURST',
'MooncoinMOON',
'WagerrWGR',
'KoreKORE',
'ClamsCLAM',
'QuantumQAU',
'LoMoCoinLMC',
'SynereoAMP',
'PRIZMPZM',
'VeriCoinVRC',
'COSSCOSS',
'PrimasPST',
'OAXOAX',
'MatchpoolGUP',
'VoiseVOISE',
'XTRABYTESXBY',
'DatabitsDTB',
'BitSendBSD',
'GambitGAM',
'DigitalNoteXDN',
'AirTokenAIR',
'Swarm CitySWT',
'DAO CasinoBET',
'HEATHEAT',
'BCAPBCAP',
'CenturionCNT',
'LampixPIX',
'SoarcoinSOAR',
'Waves Communi WCT',
'NeosCoinNEOS',
'E Dinar CoinEDR',
'InvestFeedIFT',
'vSliceVSL',
'EncryptoTel [ ETT',
'ObsidianODN',
'VoxelsVOX',
'NimiqNET',
'YocoinYOC',
'SolarCoinSLR',
'SpectrecoinXSPEC',
'MusicoinMUSIC',
'SphereSPHR',
'NuSharesNSR',
'BlockMason Cr BCPT',
'PlutonPLU',
'NVONVST',
'IncentINCNT',
'HTMLCOINHTML',
'ATC CoinATCC',
'FeathercoinFTC',
'PinkCoinPINK',
'TrueFlipTFL',
'WhiteCoinXWC',
'OBITSOBITS',
'MyBit TokenMYB',
'BridgeCoinBCO',
'BitcoreBTX',
'TaoXTO',
'iXledgerIXT',
'DubaiCoinDBIX',
'BitcrystalsBCY',
'TheGCCcoinGCC',
'NovacoinNVC',
'bitCNYBITCNY',
'AuroracoinAUR',
'CVCoinCVCOIN',
'BlocktixTIX',
'GroestlcoinGRS',
'EquiTraderEQT',
'BitBeanBITB',
'CurecoinCURE',
'SequenceSEQ',
'CreditbitCRB',
'VIBEVIBE',
'GoldCoinGLD',
'DimecoinDIME',
'PoSW CoinPOSW',
'Project DecorumPDC',
'BitlandCADASTRAL',
'NeutronNTRN',
'Global Curren GCR',
'DNotesNOTE',
'ExclusiveCoinEXCL',
'VcashXVC',
'DentDENT',
'Internet of P IOP',
'BlockCATCAT',
'BitswiftSWIFT',
'ArtByteABY',
'BlitzcashBLITZ',
'E Currency CoinECC',
'eBTCEBTC',
'ZrCoinZRC',
'FoldingCoinFLDC',
'PlusXBC',
'OracleChainOCT',
'EuropeCoinERC',
'QwarkQWARK',
'DynamicDYN',
'ZeitcoinZEIT',
'BelaBELA',
'HushHUSH',
'REALREAL',
'Pascal CoinPASC',
'StealthcoinXST',
'SynergySNRG',
'Circuits of V COVAL',
'CondensateRAIN',
'PesetacoinPTC',
'PropyPRO',
'Hubii NetworkHBT',
'ZClassicZCL',
'RemicoinRMC',
'VeriumReserveVRM',
'TerracoinTRC',
'Unity IngotUNY',
'Bitcoin',
'Ethereum',
'Bitcoin Cash',
'Ripple',
'Litecoin',
'Cardano',
'IOTA',
'Dash',
'NEM',
'Monero',
'Bitcoin Gold',
'Qtum',
'Stellar',
'NEO',
'Ethereum Classic',
'Verge',
'Lisk',
'Nxt',
'Zcash',
'Stratis',
'BitShares',
'Bytecoin',
'Waves',
'BitConnect',
'Hshare',
'Dogecoin',
'Komodo',
'Siacoin',
'Steem',
'RaiBlocks',
'DigiByte',
'Ark',
'PIVX',
'MonaCoin',
'Decred',
'ReddCoin',
'Electroneum',
'Byteball Bytes',
'Syscoin',
'BitcoinDark',
'Factom',
'ZCoin',
'VeChain',
'Vertcoin',
'GameCredits',
'BitBay',
'Cryptonex',
'Einsteinium',
'GXShares',
'Nexus',
'Blocknet',
'Ubiq',
'NAV Coin',
'DigitalNote',
'Skycoin',
'Groestlcoin',
'Particl',
'Rise',
'Asch',
'Burst',
'ZenCash',
'Peercoin',
'KuCoin Shares',
'Emercoin',
'Achain',
'XTRABYTES',
'Metaverse ETP',
'CloakCoin',
'Viacoin',
'LBRY Credits',
'Voxels',
'SaluS',
'Neblio',
'Pura',
'Counterparty',
'SmartCash',
'HempCoin',
'Feathercoin',
'Shift',
'SIBCoin',
'Elastic',
'PotCoin',
'DECENT',
'Gulden',
'WhiteCoin',
'Lykke',
'MinexCoin',
'FairCoin',
'Namecoin',
'ION',
'Aeon',
'I/O Coin',
'BlackCoin',
'Experience Po...',
'BTC',
'ETH',
'BCH',
'XRP',
'LTC',
'ADA',
'MIOTA',
'DASH',
'XEM',
'XMR',
'BTG',
'QTUM',
'XLM',
'NEO',
'ETC',
'XVG',
'LSK',
'NXT',
'ZEC',
'STRAT',
'BTS',
'BCN',
'WAVES',
'BCC',
'HSR',
'DOGE',
'KMD',
'SC',
'STEEM',
'XRB',
'DGB',
'ARK',
'PIVX',
'MONA',
'DCR',
'RDD',
'ETN',
'GBYTE',
'SYS',
'BTCD',
'FCT',
'XZC',
'VET',
'VTC',
'GAME',
'BAY',
'CNX',
'EMC2',
'GXS',
'NXS',
'BLOCK',
'UBQ',
'NAV',
'XDN',
'SKY',
'GRS',
'PART',
'RISE',
'XAS',
'BURST',
'ZEN',
'PPC',
'KCS',
'EMC',
'ACT',
'XBY',
'ETP',
'CLOAK',
'VIA',
'LBC',
'VOX',
'SLS',
'NEBL',
'PURA',
'XCP',
'SMART',
'THC',
'FTC',
'SHIFT',
'SIB',
'XEL',
'POT',
'DCT',
'NLG',
'XWC',
'LKK',
'MNX',
'FAIR',
'NMC',
'ION',
'AEON',
'IOC',
'BLK',
'XP',
'биткоин',
'криптовалюта',
'крипто'

]

to_search = [x.lower() for x in to_search]

print (len(to_search))

browser = webdriver.PhantomJS(executable_path='/../usr/local/bin/phantomjs')
morph = MorphAnalyzer()
russian_stops = stopwords.words('russian')
english_stops = stopwords.words('english')


def run_russia ():

    print("bleep")
    l='ru-ru'
    t='криптовалюта news'
    c = 'Russia'

    for i in range(2):

        links_df = pd.DataFrame()
        try:
            links_df = get_links(t,l)
        except:
            pass
        print ('длина составляет {}'.format(links_df.shape[0]))

    if links_df.shape[0]==0:
        pass
    else:

        if l =='ru-ru':
            text_df = parse_links_ru(links_df)
        else:
            text_df = parse_links(links_df)

        concated_df = find_keywords(text_df, links_df)
        concated_exclude, temp_exclude = to_exclude_text(concated_df)
        concated_cut = concated_exclude[(concated_exclude[0]!='') & (~concated_exclude[0].isnull())].reset_index(drop=True)
        concated_sims = del_interntal_duplicates(concated_cut)
        parsed_df = pd.read_excel('../output/crypto_news/parsed.xlsx')
        parsed_links = parsed_df['link']
        concated_sims = concated_sims[~concated_sims['link'].isin(parsed_links)]
        concated_sims['country'] = c
        for i, m, c in zip ( concated_sims[0], concated_sims['link'], concated_sims['country']):
            send_to_telegram(i, m, c)
            time.sleep(5)
        parsed_df_new = pd.concat([parsed_df, concated_sims[['link', 'text']]], axis=0)
        parsed_df_new.to_excel('../output/crypto_news/parsed.xlsx')
        print ('finished iteration')


def run_england ():

    print("bleep")
    l='uk-en'
    t='cryptocurrency news'
    c = 'England'

    for i in range(2):

        links_df = pd.DataFrame()
        try:
            links_df = get_links(t,l)
        except:
            pass
        print ('длина составляет {}'.format(links_df.shape[0]))
        if links_df.shape[0]==0:
            pass
        else:

            if l =='ru-ru':
                text_df = parse_links_ru(links_df)
            else:
                text_df = parse_links(links_df)

            concated_df = find_keywords(text_df, links_df)
            concated_exclude, temp_exclude = to_exclude_text(concated_df)
            concated_cut = concated_exclude[(concated_exclude[0]!='') & (~concated_exclude[0].isnull())].reset_index(drop=True)
            concated_sims = del_interntal_duplicates(concated_cut)
            parsed_df = pd.read_excel('../output/crypto_news/parsed.xlsx')
            parsed_links = parsed_df['link']
            concated_sims = concated_sims[~concated_sims['link'].isin(parsed_links)]
            concated_sims['country'] = c
            for i, m, c in zip ( concated_sims[0], concated_sims['link'], concated_sims['country']):
                send_to_telegram(i, m, c)
                time.sleep(5)
            parsed_df_new = pd.concat([parsed_df, concated_sims[['link', 'text']]], axis=0)
            parsed_df_new.to_excel('../output/crypto_news/parsed.xlsx')
            print ('finished iteration')



def run_usa ():

    print("bleep")
    l='us-en'
    t='cryptocurrency news'
    c = 'USA'

    for i in range(2):

        links_df = pd.DataFrame()
        try:
            links_df = get_links(t,l)
        except:
            pass
        print ('длина составляет {}'.format(links_df.shape[0]))

    if links_df.shape[0]==0:
        pass
    else:

        if l =='ru-ru':
            text_df = parse_links_ru(links_df)
        else:
            text_df = parse_links(links_df)

        concated_df = find_keywords(text_df, links_df)
        concated_exclude, temp_exclude = to_exclude_text(concated_df)
        concated_cut = concated_exclude[(concated_exclude[0]!='') & (~concated_exclude[0].isnull())].reset_index(drop=True)
        concated_sims = del_interntal_duplicates(concated_cut)
        parsed_df = pd.read_excel('../output/crypto_news/parsed.xlsx')
        parsed_links = parsed_df['link']
        concated_sims = concated_sims[~concated_sims['link'].isin(parsed_links)]
        concated_sims['country'] = c
        for i, m, c in zip ( concated_sims[0], concated_sims['link'], concated_sims['country']):
            send_to_telegram(i, m, c)
            time.sleep(5)
        parsed_df_new = pd.concat([parsed_df, concated_sims[['link', 'text']]], axis=0)
        parsed_df_new.to_excel('../output/crypto_news/parsed.xlsx')
        print ('finished iteration')

def run_india ():

    print("bleep")
    l='in-en'
    t='cryptocurrency news'
    c = 'India'

    for i in range(2):

        links_df = pd.DataFrame()
        try:
            links_df = get_links(t,l)
        except:
            pass
        print ('длина составляет {}'.format(links_df.shape[0]))
    if links_df.shape[0]==0:
        pass

    else:
        if l =='ru-ru':
            text_df = parse_links_ru(links_df)
        else:
            text_df = parse_links(links_df)

        concated_df = find_keywords(text_df, links_df)
        concated_exclude, temp_exclude = to_exclude_text(concated_df)
        concated_cut = concated_exclude[(concated_exclude[0]!='') & (~concated_exclude[0].isnull())].reset_index(drop=True)
        try:
            concated_sims = del_interntal_duplicates(concated_cut)
            parsed_df = pd.read_excel('../output/crypto_news/parsed.xlsx')
            parsed_links = parsed_df['link']
            concated_sims = concated_sims[~concated_sims['link'].isin(parsed_links)]
            concated_sims['country'] = c
            for i, m, c in zip ( concated_sims[0], concated_sims['link'], concated_sims['country']):
                send_to_telegram(i, m, c)
                time.sleep(5)
            parsed_df_new = pd.concat([parsed_df, concated_sims[['link', 'text']]], axis=0)
            parsed_df_new.to_excel('../output/crypto_news/parsed.xlsx')
            print ('finished iteration')
        except:
            print ('что-то пошло не так')
            pass


# очистить результаты
# temp = pd.read_excel('../output/crypto_news/parsed.xlsx')
# temp[:250].to_excel('../output/crypto_news/parsed.xlsx', index=False)


import schedule
import time

for i in range(100):

    run_england()
    time.sleep(3600)
    run_usa()
    time.sleep(3600)
    run_india()
    time.sleep(3600)
    run_russia()
    time.sleep(3600)

# schedule.every().day.at("8:00").do(run_russia)
# schedule.every().day.at("11:00").do(run_england)
# schedule.every().day.at("16:00").do(run_usa)
# schedule.every().day.at("5:30").do(run_india)
#
#
# while True:
#     schedule.run_pending()
#     time.sleep(1)
