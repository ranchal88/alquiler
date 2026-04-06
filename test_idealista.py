from src.extractors.idealista.extractor import extract_neighborhood  
print('start')  
try:  
    listings = extract_neighborhood('trafalgar','chamberi',pages=1)  
    print('listings', len(listings))  
except Exception as e:  
    import traceback; traceback.print_exc()  
