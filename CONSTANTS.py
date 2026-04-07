'''
Filters:
Code: P - Purchase
Filed Date: Last 60 days
Traded value: > $1000K dollars
Insider Title: CEO, COO, CFO, Director
Own Change %: > 10%
Max Results: 100
'''
OPENINSIDER_WITH_FILTERS_URL = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=60&fdr=&td=60&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=1000&vh=&ocl=10&och=&sic1=-1&sicl=100&sich=9999&isceo=1&iscoo=1&iscfo=1&isdirector=1&grp=0&nfl=&nfh=&nil=3&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
OPENINSIDER_WITH_FILTERS_TICKER_URL = "http://openinsider.com/screener?s={}&o=&pl=&ph=&ll=&lh=&fd=60&fdr=&td=60&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"

# Number of days to look back from the latest Trade Date in a ticker group
# to count how many transactions fall within that rolling window (cluster signal).
CLUSTER_ROLLING_WINDOW = 14  # days
