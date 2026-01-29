"""
LinkedIn Sector/Industry Mappings

This module contains comprehensive mappings between user-friendly sector names
and LinkedIn's internal industry IDs (f_I parameter values).

Based on LinkedIn Industry Codes V2 (434 total industries).
"""

# Sector/Industry mapping for Turkish-English matching
# Maps user input keywords to normalized sector keys
SECTOR_MAPPINGS = {
    # Technology & IT
    'technology': [
        'technology', 'bilgi teknolojisi', 'bt', 'information technology', 'it',
        'bt hizmetleri', 'bilgi teknolojisi ve hizmetleri', 'information technology and services',
        'tech', 'software', 'yazılım', 'it services', 'bt danışmanlığı'
    ],
    'bt': [
        'bt', 'bilgi teknolojisi', 'technology', 'information technology', 'it',
        'bt hizmetleri', 'bilgi teknolojisi ve hizmetleri', 'it services', 'it consulting'
    ],
    'software': [
        'software', 'yazılım', 'software development', 'yazılım geliştirme',
        'computer software', 'application software', 'software products'
    ],
    'it_services': [
        'it services', 'bt hizmetleri', 'it consulting', 'bt danışmanlığı',
        'computer services', 'information technology services'
    ],
    'telecommunications': [
        'telecommunications', 'telekomünikasyon', 'telecom', 'telekom',
        'wireless', 'mobile communications', 'telephony'
    ],
    'internet': [
        'internet', 'web', 'online', 'digital', 'e-commerce', 'ecommerce',
        'online marketplace', 'social media', 'social networking'
    ],
    
    # Financial Services
    'finance': [
        'finance', 'finans', 'financial services', 'finansal hizmetler',
        'banking', 'bankacılık', 'investment', 'yatırım'
    ],
    'banking': [
        'banking', 'bankacılık', 'banks', 'banka', 'commercial banking',
        'savings institutions', 'credit intermediation'
    ],
    'insurance': [
        'insurance', 'sigorta', 'insurance carriers', 'sigorta şirketleri',
        'insurance agencies', 'life insurance', 'property insurance'
    ],
    'investment': [
        'investment', 'yatırım', 'investment banking', 'investment management',
        'capital markets', 'venture capital', 'private equity'
    ],
    
    # Healthcare
    'healthcare': [
        'healthcare', 'sağlık', 'health', 'sağlık hizmetleri',
        'medical', 'tıbbi', 'hospital', 'hastane'
    ],
    'hospitals': [
        'hospitals', 'hastane', 'hospital', 'medical centers',
        'healthcare facilities', 'healthcare services'
    ],
    'medical_practices': [
        'medical practices', 'tıbbi uygulamalar', 'physicians', 'doctors',
        'dentists', 'clinics', 'medical clinics'
    ],
    'pharmaceuticals': [
        'pharmaceuticals', 'ilaç', 'pharmaceutical manufacturing', 'drug manufacturing',
        'pharma', 'biotechnology', 'biyoteknoloji'
    ],
    
    # Manufacturing
    'manufacturing': [
        'manufacturing', 'imalat', 'üretim', 'production',
        'industrial', 'endüstriyel', 'factory', 'fabrika'
    ],
    'automotive': [
        'automotive', 'otomotiv', 'motor vehicles', 'car manufacturing',
        'automobile', 'vehicle manufacturing'
    ],
    'electronics': [
        'electronics', 'elektronik', 'electronic manufacturing',
        'computer hardware', 'semiconductors', 'consumer electronics'
    ],
    'food_manufacturing': [
        'food manufacturing', 'gıda üretimi', 'food processing',
        'beverage manufacturing', 'food and beverage'
    ],
    'chemicals': [
        'chemicals', 'kimya', 'chemical manufacturing', 'pharmaceutical manufacturing',
        'petrochemicals', 'specialty chemicals'
    ],
    
    # Education
    'education': [
        'education', 'eğitim', 'educational services', 'eğitim hizmetleri',
        'schools', 'okullar', 'universities', 'üniversiteler'
    ],
    'higher_education': [
        'higher education', 'yüksek öğretim', 'universities', 'üniversiteler',
        'colleges', 'kolejler', 'academic institutions'
    ],
    'primary_education': [
        'primary education', 'ilköğretim', 'secondary education', 'ortaöğretim',
        'k-12', 'schools', 'okullar'
    ],
    'e_learning': [
        'e-learning', 'online education', 'online learning', 'uzaktan eğitim',
        'digital education', 'edtech', 'educational technology'
    ],
    
    # Retail
    'retail': [
        'retail', 'perakende', 'retail trade', 'retail stores',
        'shopping', 'alışveriş', 'retailers'
    ],
    'ecommerce': [
        'ecommerce', 'e-commerce', 'online retail', 'online shopping',
        'internet retail', 'digital commerce'
    ],
    'fashion': [
        'fashion', 'moda', 'apparel', 'clothing', 'textile',
        'fashion retail', 'apparel retail'
    ],
    'grocery': [
        'grocery', 'market', 'supermarket', 'süpermarket',
        'food retail', 'grocery stores'
    ],
    
    # Professional Services
    'professional_services': [
        'professional services', 'profesyonel hizmetler', 'consulting',
        'danışmanlık', 'business services'
    ],
    'consulting': [
        'consulting', 'danışmanlık', 'business consulting', 'management consulting',
        'strategy consulting', 'it consulting'
    ],
    'legal': [
        'legal', 'hukuk', 'law', 'law firms', 'legal services',
        'attorneys', 'lawyers', 'avukat'
    ],
    'accounting': [
        'accounting', 'muhasebe', 'accounting services', 'bookkeeping',
        'tax services', 'financial accounting'
    ],
    'architecture': [
        'architecture', 'mimarlık', 'architectural services',
        'architecture and planning', 'design services'
    ],
    'engineering': [
        'engineering', 'mühendislik', 'engineering services',
        'civil engineering', 'mechanical engineering', 'electrical engineering'
    ],
    
    # Construction
    'construction': [
        'construction', 'inşaat', 'building construction', 'yapı',
        'construction services', 'general contractors'
    ],
    'building_construction': [
        'building construction', 'bina inşaatı', 'residential construction',
        'commercial construction', 'construction contractors'
    ],
    'civil_engineering': [
        'civil engineering', 'inşaat mühendisliği', 'infrastructure',
        'public works', 'highway construction'
    ],
    
    # Transportation & Logistics
    'transportation': [
        'transportation', 'ulaştırma', 'logistics', 'lojistik',
        'shipping', 'nakliye', 'freight'
    ],
    'logistics': [
        'logistics', 'lojistik', 'supply chain', 'tedarik zinciri',
        'warehousing', 'depolama', 'distribution'
    ],
    'aviation': [
        'aviation', 'havacılık', 'airlines', 'havayolları',
        'aerospace', 'aircraft', 'air transportation'
    ],
    'shipping': [
        'shipping', 'denizcilik', 'maritime', 'maritime transportation',
        'freight', 'cargo', 'shipbuilding'
    ],
    
    # Real Estate
    'real_estate': [
        'real estate', 'gayrimenkul', 'property', 'emlak',
        'real estate services', 'property management'
    ],
    'property_development': [
        'property development', 'gayrimenkul geliştirme',
        'real estate development', 'construction and development'
    ],
    
    # Utilities & Energy
    'utilities': [
        'utilities', 'kamu hizmetleri', 'public utilities',
        'electric power', 'water supply', 'natural gas'
    ],
    'energy': [
        'energy', 'enerji', 'power generation', 'electric power',
        'renewable energy', 'yenilenebilir enerji', 'solar', 'wind'
    ],
    'oil_gas': [
        'oil and gas', 'petrol ve gaz', 'petroleum', 'petrol',
        'natural gas', 'doğal gaz', 'oil extraction'
    ],
    
    # Entertainment & Media
    'entertainment': [
        'entertainment', 'eğlence', 'media', 'medya',
        'broadcasting', 'yayıncılık', 'television', 'radio'
    ],
    'media': [
        'media', 'medya', 'publishing', 'yayıncılık',
        'broadcast media', 'news media', 'digital media'
    ],
    'gaming': [
        'gaming', 'oyun', 'video games', 'computer games',
        'mobile games', 'game development'
    ],
    
    # Consumer Services
    'consumer_services': [
        'consumer services', 'tüketici hizmetleri', 'personal services',
        'household services', 'consumer goods'
    ],
    'hospitality': [
        'hospitality', 'konaklama', 'hotels', 'oteller',
        'tourism', 'turizm', 'accommodation'
    ],
    'restaurants': [
        'restaurants', 'restoranlar', 'food service', 'catering',
        'food and beverage', 'dining'
    ],
    
    # Administrative Services
    'administrative': [
        'administrative services', 'idari hizmetler', 'office administration',
        'business support', 'facilities services'
    ],
    'staffing': [
        'staffing', 'işe alım', 'recruiting', 'recruitment',
        'human resources', 'hr services', 'temporary help'
    ],
    'security': [
        'security', 'güvenlik', 'security services', 'guards',
        'surveillance', 'security systems'
    ],
    
    # Wholesale
    'wholesale': [
        'wholesale', 'toptan', 'wholesale trade', 'distribution',
        'wholesalers', 'toptan satış'
    ],
    
    # Government
    'government': [
        'government', 'devlet', 'public sector', 'kamu sektörü',
        'public administration', 'government administration'
    ],
    
    # Agriculture
    'agriculture': [
        'agriculture', 'tarım', 'farming', 'çiftçilik',
        'agricultural', 'crop production', 'livestock'
    ],
    
    # Mining
    'mining': [
        'mining', 'madencilik', 'mineral extraction',
        'metal mining', 'coal mining'
    ],
}

# LinkedIn Sector ID mapping (f_I parameter values)
# These are LinkedIn's internal industry/vertical IDs from Industry Codes V2
# Format: 'normalized_key': [list of LinkedIn industry IDs]
LINKEDIN_SECTOR_IDS = {
    # Technology & IT
    'technology': ['96', '1594', '6'],  # IT Services, Technology/Information/Media, Technology/Information/Internet
    'bt': ['96'],  # IT Services and IT Consulting
    'software': ['4'],  # Software Development
    'it_services': ['96'],  # IT Services and IT Consulting
    'telecommunications': ['8'],  # Telecommunications
    'internet': ['6'],  # Technology, Information and Internet
    
    # Financial Services
    'finance': ['43'],  # Financial Services
    'banking': ['41'],  # Banking
    'insurance': ['42'],  # Insurance
    'investment': ['45', '46', '106'],  # Investment Banking, Investment Management, Venture Capital
    
    # Healthcare
    'healthcare': ['14'],  # Hospitals and Health Care
    'hospitals': ['2081'],  # Hospitals
    'medical_practices': ['13'],  # Medical Practices
    'pharmaceuticals': ['15'],  # Pharmaceutical Manufacturing
    
    # Manufacturing
    'manufacturing': ['25'],  # Manufacturing
    'automotive': ['53', '1042'],  # Motor Vehicle Manufacturing, Motor Vehicle Parts
    'electronics': ['24', '7'],  # Computers and Electronics, Semiconductor Manufacturing
    'food_manufacturing': ['23'],  # Food and Beverage Manufacturing
    'chemicals': ['54'],  # Chemical Manufacturing
    
    # Education
    'education': ['1999'],  # Education
    'higher_education': ['68'],  # Higher Education
    'primary_education': ['67'],  # Primary and Secondary Education
    'e_learning': ['132'],  # E-Learning Providers
    
    # Retail
    'retail': ['27'],  # Retail
    'ecommerce': ['1445'],  # Online and Mail Order Retail
    'fashion': ['19'],  # Retail Apparel and Fashion
    'grocery': ['22'],  # Retail Groceries
    
    # Professional Services
    'professional_services': ['1810'],  # Professional Services
    'consulting': ['11'],  # Business Consulting and Services
    'legal': ['10'],  # Legal Services
    'accounting': ['47'],  # Accounting
    'architecture': ['50'],  # Architecture and Planning
    'engineering': ['3242'],  # Engineering Services
    
    # Construction
    'construction': ['48'],  # Construction
    'building_construction': ['406'],  # Building Construction
    'civil_engineering': ['51'],  # Civil Engineering
    
    # Transportation & Logistics
    'transportation': ['116'],  # Transportation, Logistics, Supply Chain and Storage
    'logistics': ['116', '93'],  # Transportation/Logistics, Warehousing and Storage
    'aviation': ['94'],  # Airlines and Aviation
    'shipping': ['95', '58'],  # Maritime Transportation, Shipbuilding
    
    # Real Estate
    'real_estate': ['44'],  # Real Estate
    'property_development': ['44'],  # Real Estate (includes development)
    
    # Utilities & Energy
    'utilities': ['59'],  # Utilities
    'energy': ['383', '3240'],  # Electric Power Generation, Renewable Energy Power Generation
    'oil_gas': ['57'],  # Oil and Gas
    
    # Entertainment & Media
    'entertainment': ['28'],  # Entertainment Providers
    'media': ['1594'],  # Technology, Information and Media
    'gaming': ['109'],  # Computer Games
    
    # Consumer Services
    'consumer_services': ['91'],  # Consumer Services
    'hospitality': ['31', '2194'],  # Hospitality, Hotels and Motels
    'restaurants': ['32'],  # Restaurants
    
    # Administrative Services
    'administrative': ['1912'],  # Administrative and Support Services
    'staffing': ['104'],  # Staffing and Recruiting
    'security': ['121'],  # Security and Investigations
    
    # Wholesale
    'wholesale': ['133'],  # Wholesale
    
    # Government
    'government': ['75'],  # Government Administration
    
    # Agriculture
    'agriculture': ['201'],  # Farming, Ranching, Forestry
    
    # Mining
    'mining': ['56'],  # Mining
}
