####################################################################################################

VIDEO_PREFIX = "/video/sickbeard"

NAME = L('SickBeard')

ART         = 'art-default.jpg'
ICON        = 'icon-default.png'
SEARCH_ICON = 'icon-search.png'
PREFS_ICON  = 'icon-prefs.png'
SB_URL      = 'http://'+Prefs['sbIP']+':'+Prefs['sbPort']
PLEX_URL    = 'http://'+Prefs['plexIP']+':32400'
TV_SECTION  = ""

####################################################################################################

def Start():
    Plugin.AddPrefixHandler(VIDEO_PREFIX, MainMenu, L('SickBeard'), ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    HTTP.CacheTime=3600*3
    if Prefs['sbUser'] and Prefs['sbPass']:
        HTTP.SetPassword(url=SB_URL, username=Prefs['sbUser'], password=Prefs['sbPass'])

    global TV_SECTION
    TV_SECTION = GetTvSectionID()
    if TV_SECTION == "":
        return MessageContainer('SickBeard Plugin', L('Unable to locate Plex library TV metadata. Check Plugin Prefs.'))

####################################################################################################

def MainMenu():
    dir = MediaContainer(viewGroup="InfoList")

    dir.Append(Function(DirectoryItem(ComingEpisodes,"Coming Episodes","Soon to be aired",
            summary="See which shows that you follow have episodes airing soon",thumb=R(ICON),art=R(ART))))
    dir.Append(Function(DirectoryItem(ShowList,"All Shows","SickBeard List",
            summary="See details about all shows which SickBeard manages for you",thumb=R(ICON),art=R(ART))))
    dir.Append(Function(InputDirectoryItem(SearchResults,"Add Show","Add new show to SickBeard",
            summary="Search by name to add a new show to SickBeard's watch list",thumb=R(SEARCH_ICON),art=R(ART))))
    dir.Append(PrefsItem(title="Preferences",subtitle="SickBeard plugin prefs",
        summary="Set SickBeard plugin preferences to allow it to connect to SickBeard app",thumb=R(PREFS_ICON)))

    return dir

####################################################################################################

def ComingEpisodes(sender):
    dir = MediaContainer(ViewGroup='InfoList', title2='Coming Episodes')
    url = SB_URL + '/comingEpisodes'
    episodesPage = HTML.ElementFromURL(url, errors='ignore', cacheTime=0)
    
    for episode in episodesPage.xpath('//div[@class="listing"]'):
        showName    = episode.xpath('a')[0].get('name')
        #Log('Found: '+ showName)
        airsNext    = episode.xpath('div/p[1]/span')[1].text
        timeSlot    = episode.xpath('div/p[2]/span')[3].text
        updateUrl   = episode.xpath('.//a[@class="forceUpdate"]')[0].get('href')
        #Log(updateUrl)
        dir.Append(Function(PopupDirectoryItem(EpisodeSelectMenu,title=showName,subtitle="Airs: "+timeSlot,
            summary="Next episode: "+airsNext, thumb=Function(GetSeriesThumb, showName=showName)),url=updateUrl))
    
    return dir

####################################################################################################

def SearchResults(sender,query):
    dir = MediaContainer(ViewGroup="InfoList",title2="Search Results")
    
    #tell SickBeard to create the folder in the TV directory
    newShowFolder = String.Quote(Prefs['tvDir']+'/'+query, usePlus=True)
    Log(newShowFolder)
    addFolderUrl = SB_URL+'/home/addShows/addShows/?showDirs='+newShowFolder
    url = SB_URL + '/home/addShows/searchTVDBForShowName?name=' + String.Quote(query, usePlus=True)
    
    addFolderResult = HTTP.Request(addFolderUrl).content
    tvdbResult = JSON.ObjectFromURL(url).get("results")
    
    for item in tvdbResult:
        tvdbID = item[0]
        showName = item[1]
        startDate = item[2]
        if startDate == None:
            startDate = "Unknown"
        Log("Found: " +showName)
        dir.Append(Function(DirectoryItem(AddShow,title=showName,subtitle="TVDB: "+str(tvdbID),
            summary="First aired: "+startDate),name=showName,ID=tvdbID))
    
    return dir
    
####################################################################################################  

def ShowList(sender):
    '''List all shows that SickBeard manages, and relevant info about each show'''
    dir = MediaContainer(ViewGroup="InfoList", title2="All Shows")
    url = SB_URL + '/home/'
    showsPage = HTML.ElementFromURL(url, errors='ignore', cacheTime=0)
    for show in showsPage.xpath('//tr[@class="evenLine"]'):
        #try:
        next    = show.xpath('td')[0].text
        if next == None:
            next = "unknown"
        #Log('Next airs: '+next)
        name    = show.xpath('td[2]//text()')[0]
        #Log(name)
        link  = show.xpath('td[2]/a')[0].get('href')
        #Log(link)
        showID = str(link)[-5:]
        #Log(showID)
        network = show.xpath('td')[2].text
        if network == None:
            network = "unknown"
        #Log('Network: '+network)
        quality = str(show.xpath('td')[3].text)[2:]
        #Log('Download quatlity: '+quality)
        episodes = str(show.xpath('td[5]/comment()')[0])[4:-3]
        #Log(episodes)
        status  = show.xpath('td')[6].text
        if status == None:
            status = "Not Available"
        #Log("Status: "+status)
        showSummary = GetSummary(name)
        if showSummary == None:
            showSummary = "Not available"
        if status == "Continuing":
            info    = ('Next Episode: ' + str(next) + '\n' +
                    'Airs on: ' + network + '\n' +
                    'Status: ' + status + '\n' +
                    'Download quality: ' + quality + '\n' +
                    'Summary: ' + showSummary)
        else:
            info    = ('Aired on: ' + network + '\n' +
                    'Status: ' + status + '\n' +
                    'Download quality: ' + quality + '\n' +
                    'Summary: ' + showSummary)
        #except:
        #    pass
        updateUrl = '/home/updateShow?show=' + showID +'&force=1'
        dir.Append(Function(PopupDirectoryItem(SeriesSelectMenu, title=name, infoLabel=episodes,
            subtitle='Episodes: '+episodes, summary=info, thumb=Function(GetSeriesThumb, showName=name)),
            showID=showID, showName=name))
    return dir
    
####################################################################################################    

def SeriesSelectMenu(sender, showID, showName):
    '''display a popup menu with the option to force a search for the selected episode/series'''
    dir = MediaContainer(title='')
    dir.Append(Function(PopupDirectoryItem(SeasonList, title="View Episode List"), showID=showID,
        showName=showName))
    dir.Append(Function(PopupDirectoryItem(EditSeries, title="Edit SickBeard options for this series"),
        showID=showID, showName=showName))
    #dir.Append(Function(PopupDirectoryItem(SeriesRefresh, title="Force search for this series"), showID=showID))
    
    return dir
    
####################################################################################################

def EpisodeSelectMenu(sender, url="", showID="", seasonNum="", episodeNum=""):
    '''display a popup menu with the option to force a search for the selected episode/series'''
    dir = MediaContainer(title='')
    if url != "":
        dir.Append(Function(PopupDirectoryItem(EpisodeRefresh, title="Force search for this episode"),
            url=url))
    else:
        dir.Append(Function(PopupDirectoryItem(EpisodeRefresh, title="Force search for this episode"),
            showID=showID, seasonNum=seasonNum, episodeNum=episodeNum))
        dir.Append(Function(PopupDirectoryItem(MarkEpisodeWanted, title="Mark this episode as wanted"),
            showID=showID, seasonNum=seasonNum, episodeNum=episodeNum))
    return dir
    
####################################################################################################

def AddShow(sender, name, ID):
    '''Tell SickBeard to add the given show to the watched/wanted list'''
    dir = MessageContainer("SickBeard", L('Show added to list'))
    if str(Prefs['tvDir'])[-1] == '/':
        postValues = {'whichSeries' : str(ID), 'skipShow' : "0", 'showToAdd' : String.Quote(Prefs['tvDir']+name, usePlus=True)}
    else:
        postValues = {'whichSeries' : str(ID), 'skipShow' : "0", 'showToAdd' : String.Quote(Prefs['tvDir']+'/'+name, usePlus=True)}
    url = SB_URL + '/home/addShows/addSingleShow'
    Log(postValues['showToAdd'])
    redirect = HTTP.Request(url, postValues).content
    
    #Log(str(result))
    
    return dir
    
####################################################################################################

def GetSeriesThumb(showName):
    '''retrieve the thumbnail image from the Plex metadata database based on the title of the series'''

    tv_section_url = PLEX_URL + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore')
    try:
        seriesThumb = tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('thumb')
        data = HTTP.Request(PLEX_URL + seriesThumb, cacheTime=CACHE_1MONTH).content
        return DataObject(data, 'image/jpeg')
    except:
        return Redirect(R(ICON))

####################################################################################################

def GetSeasonThumb(showName, seasonInt):
    '''retrieve the season thumbnail image from the Plex metadata database based on the title of the series'''
    seasonString = "season " + seasonInt
    Log("Getting thumb for " + seasonString)
    tv_section_url = PLEX_URL + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore')
    try:
        seasonListUrl = PLEX_URL + tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('key')
        seasonListPage = HTML.ElementFromURL(seasonListUrl, errors='ignore')
        seasonThumb = seasonListPage.xpath('//directory[@index='+seasonInt+']')[0].get('thumb')
        data = HTTP.Request(PLEX_URL + seasonThumb, cacheTime=CACHE_1MONTH).content
        return DataObject(data, 'image/jpeg')
    except:
        return GetSeriesThumb(showName)

####################################################################################################

def GetTvSectionID():
    '''Determine what section(s) are TV series in Plex library'''
    
    library = HTML.ElementFromURL(PLEX_URL+'/library/sections')
    sectionID = library.xpath('//directory[@type="show"]')[0].get('key')
    #sectionID = library.xpath('//directory[@title="'+Prefs['tvSection']+'"]')[0].get('key')
    #Log('TV section ID: ' + sectionID)
    return sectionID
    
####################################################################################################

def GetSummary(showName):
    '''retrieve the series summary from the Plex metadata database based on the title of the series'''

    tv_section_url = PLEX_URL + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore', cacheTime=CACHE_1MONTH)
    try:
        summary = tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('summary')
    except:
        summary = "Not found."
    
    return summary

####################################################################################################

def SeasonList(sender, showID, showName):
    '''Display a list of all season of the given TV series in SickBeard'''
    seasonListUrl = SB_URL + '/home/displayShow?show=' + showID
    dir = MediaContainer(ViewGroup='InfoList', title2=showName)
    listPage = HTML.ElementFromURL(seasonListUrl, errors='ignore')
    seasonList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    for season in seasonList.xpath('//input[@class="seasonCheck"]'):
        seasonNum = season.get('id')
        dir.Append(Function(DirectoryItem(EpisodeList, title='Season '+seasonNum, subtitle=showName,
            thumb=Function(GetSeasonThumb, showName=showName, seasonInt=seasonNum)),
            showID=showID, showName=showName, seasonInt=seasonNum))
    
    return dir

####################################################################################################

def EpisodeList(sender, showID, showName, seasonInt):
    '''Display alist of all episodes of the given TV series including the SickBeard state of each'''
    episodeListUrl = SB_URL + '/home/displayShow?show=' + showID
    dir = MediaContainer(ViewGroup='InfoList', title2=showName)

    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore', cacheTime=0)
    episodeList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    for episode in episodeList.xpath('//tr'):
        if episode.get('class') == "seasonheader":
            pass
        elif episode.get('class') == None:
            pass
        else:
            epNum = episode.xpath('.//a')[0].get('name')
            if str(epNum)[0:len(str(seasonInt))] == seasonInt:
                epNum = str(epNum)[(len(str(seasonInt))+1):]
                #Log('Found: Season ' + seasonInt + ' Episode' + epNum)
                epTitle = str(episode.xpath('./td')[4].text)[10:-10]
                #Log('Title: ' + epTitle)
                epDate = episode.xpath('./td')[5].text
                #Log('AirDate: ' + epDate)
                epFile = str(episode.xpath('./td')[6].text)[2:-7]
                #Log(epFile)
                epStatus = episode.xpath('./td')[7].text
                #Log('Status: ' + epStatus
                dir.Append(Function(PopupDirectoryItem(EpisodeSelectMenu, title=epNum+' '+epTitle,
                    infoLabel=epStatus, subtitle='Status: '+epStatus,
                    summary="Airdate: "+epDate+"\nFileName: "+epFile,
                    thumb=Function(GetSeriesThumb, showName=showName)), showID=showID, seasonNum=seasonInt,
                    episodeNum=epNum))
        
    return dir

####################################################################################################

def EditSeries(sender, showID, showName):
    '''display a menu of options for editing SickBeard functions for the given series'''
    dir = MediaContainer(ViewGroup='InfoList', title2='Edit '+showName)
    
    dir.Append(Function(PopupDirectoryItem(RescanFiles, 'Re-Scan Files', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID))
    dir.Append(Function(PopupDirectoryItem(RenameEpisodes, 'Rename Episodes', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID))
    dir.Append(Function(PopupDirectoryItem(ForceFullUpdate, 'Force Full Update', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID))
    dir.Append(Function(PopupDirectoryItem(DeleteShow, 'Delete Series', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID))
    
    return dir
####################################################################################################

def ForceFullUpdate(sender, showID):
    '''tell SickBeard to do a force search for the given series'''
    updateUrl = SB_URL + '/home/updateShow?show=' + showID +'&force=1'
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Force search started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable force search'))

####################################################################################################

def RescanFiles(sender, showID):
    '''tell SickBeard to do re-scan files for the given series'''
    updateUrl = SB_URL + '/home/refreshShow?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Full file scan started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable to start file scan'))

####################################################################################################

def RenameEpisodes(sender, showID):
    '''tell SickBeard to do fix episode names for the given series'''
    updateUrl = SB_URL + '/home/fixEpisodeNames?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Episode renaming process started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable to start renaming process'))

####################################################################################################

def PauseSeries(sender, showID): #not implemented yet
    '''tell sickbeard to pause the given series'''
    return
####################################################################################################

def DeleteShow(sender, showID):
    '''tell SickBeard to do delete the given series'''
    updateUrl = SB_URL + '/home/deleteShow?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Series deleted from SickBeard database'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable to delete series'))

####################################################################################################

def EpisodeRefresh(sender, url="", showID="", seasonNum="", episodeNum=""):
    '''tell SickBeard to do a force search for the given episode'''
    if url != "":
        updateUrl = SB_URL + url
        #Log(updateUrl)
    elif showID != "":
        updateUrl = SB_URL + 'home/searchEpisode?show='+showID+'&season='+seasonNum+'&episode='+episodeNum
    else:
        return MessageContainer('SickBeard Plugin', L('Episode never aired. Cannot force search.'))
    
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Force search started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable force search'))

####################################################################################################

def MarkEpisodeWanted(sender, showID, seasonNum, episodeNum):
    '''tell SickBeard to do mark the given episode as "wanted"'''
    
    url = SB_URL + '/home/setStatus?show='+showID+'&eps='+seasonNum+'x'+episodeNum+'&status=3'
    
    try:
        rsult = HTTP.Request(url, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Episode marked as wanted'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable mark as wanted'))

####################################################################################################