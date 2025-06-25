from sfinance.sfinance import SFinance
sf = SFinance("https://www.screener.in/")
t = sf.ticker("INFY")
print(t.get_overview())
print(t.get_income_statement())
sf.close()
