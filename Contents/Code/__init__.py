import re, os, subprocess

####################################################################################################

VIDEO_PREFIX = "/video/sickbeard"

NAME = 'SickBeard'

ART         = 'art-default.jpg'
ICON        = 'icon-default.png'
SEARCH_ICON = 'icon-search.png'
PREFS_ICON  = 'icon-prefs.png'
TV_SECTION  = ""

###a temporary standin for yet to be implemented prefs['ArchiveDelete']###
#ALLOW_DELETE = False

####################################################################################################

def Start():
    Plugin.AddPrefixHandler(VIDEO_PREFIX, MainMenu, L('SickBeard'), ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    HTTP.CacheTime=3600*3
     
    global TV_SECTION
    TV_SECTION = GetTvSectionID()
    if TV_SECTION == "":
        return MessageContainer('SickBeard Plugin', L('Unable to locate Plex library TV metadata. Check Plugin Prefs.'))

    if Prefs['sbUser'] and Prefs['sbPass']:
        HTTP.SetPassword(url=Get_SB_URL(), username=Prefs['sbUser'], password=Prefs['sbPass'])
    
####################################################################################################

def ValidatePrefs():

    if Prefs['sbUser'] and Prefs['sbPass']:
        HTTP.SetPassword(url=Get_SB_URL(), username=Prefs['sbUser'], password=Prefs['sbPass'])

    Restart()

    return

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
    
    #if ALLOW_DELETE:
    #    dir.Append(Function(DirectoryItem(RecentlyViewedMenu, title='Archive/Delete Recently Viewed',
    #        subtitle='Mark episodes as "Archived" in SickBeard and remove file',
    #        summary='Use with EXTREME CAUTION!!! \n  This will allow you to DELETE FILES from your hard drive.'+
    #        ' By using this function, you agree that you will not hold responsible the author of this plugin,'+
    #        ' the developers of Plex, or anyone other than yourself for the deletion of files. This is provided'+
    #        ' free of charge with NO WARRANTY written, implied, or otherwise. \nCONSIDER YOURSELF WARNED.')))

    updateValues = CheckForUpdate()
    if updateValues['available']:
        dir.Append(Function(PopupDirectoryItem(UpdateSB, 'SickBeard Update Available',
            'May require you to restart SickBeard', 'Depending on your set-up, you may need to restart' +
            ' SickBeard after updating.', thumb=R(ICON)), link = updateValues['link']))

    return dir

####################################################################################################

def ComingEpisodes(sender):
    dir = MediaContainer(ViewGroup='InfoList', title2='Coming Episodes')
    url = Get_SB_URL() + '/comingEpisodes'
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
    #Log(newShowFolder)
    addFolderUrl = Get_SB_URL()+'/home/addShows/addShows/?showDirs='+newShowFolder
    url = Get_SB_URL() + '/home/addShows/searchTVDBForShowName?name=' + String.Quote(query, usePlus=True)
    
    addFolderResult = HTTP.Request(addFolderUrl).content
    tvdbResult = JSON.ObjectFromURL(url).get("results")
    
    for item in tvdbResult:
        tvdbID = item[0]
        showName = item[1]
        startDate = item[2]
        if startDate == None:
            startDate = "Unknown"
        #Log("Found: " +showName)
        dir.Append(Function(DirectoryItem(AddShow,title=showName,subtitle="TVDB: "+str(tvdbID),
            summary="First aired: "+startDate),name=showName,ID=tvdbID))
    
    return dir
    
####################################################################################################  

def ShowList(sender):
    '''List all shows that SickBeard manages, and relevant info about each show'''
    dir = MediaContainer(ViewGroup="InfoList", title2="All Shows")
    url = Get_SB_URL() + '/home/'
    showsPage = HTML.ElementFromURL(url, errors='ignore', cacheTime=0)
    for show in showsPage.xpath('//tr[@class="evenLine"]'):
        next    = show.xpath('td')[0].text
        if next == None:
            next = "unknown"
        #Log('Next airs: '+next)
        name    = show.xpath('td[2]//text()')[0]
        #Log(name)
        try:
            link  = show.xpath('td[2]/a')[0].get('href')
        except:
            dir.Append(Function(PopupDirectoryItem(SeriesSelectMenu, title=name, infoLabel='???',
                subtitle='Episodes: ???', summary='Unable to find showID for this series in SickBeard. Please' +
                'check the web interface to confirm that this series was properly added. No functions will work for' + 
                'this series at this time.', thumb=Function(GetSeriesThumb, showName=name)),showID=None, showName=None))
            pass
        #Log(link)
        showID = re.findall('=(\d+)$', link)[0]
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

        updateUrl = '/home/updateShow?show=' + showID +'&force=1'
        dir.Append(Function(PopupDirectoryItem(SeriesSelectMenu, title=name, infoLabel=episodes,
            subtitle='Episodes: '+episodes, summary=info, thumb=Function(GetSeriesThumb, showName=name)),
            showID=showID, showName=name))
    return dir
    
####################################################################################################    

def SeriesSelectMenu(sender, showID, showName):
    '''display a popup menu with the option to force a search for the selected series'''
    dir = MediaContainer(title='')
    dir.Append(Function(DirectoryItem(SeasonList, title="View Season List"), showID=showID,
        showName=showName))
    
    if Client.Platform == ClientPlatform.iOS:
        dir.Append(Function(PopupDirectoryItem(EditSeries, title="Edit SickBeard series options"),
            showID=showID, showName=showName))
    else:
        dir.Append(Function(DirectoryItem(EditSeries, title="Edit SickBeard series options"),
            showID=showID, showName=showName))
    
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
    url = Get_SB_URL() + '/home/addShows/addSingleShow'
    #Log(postValues['showToAdd'])
    redirect = HTTP.Request(url, postValues).content
    
    #Log(str(result))
    
    return dir
    
####################################################################################################

def GetSeriesThumb(showName):
    '''retrieve the thumbnail image from the Plex metadata database based on the title of the series'''

    tv_section_url = Get_PMS_URL() + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore')
    try:
        seriesThumb = tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('thumb')
        data = HTTP.Request(Get_PMS_URL() + seriesThumb, cacheTime=CACHE_1MONTH).content
        return DataObject(data, 'image/jpeg')
    except:
        return Redirect(R(ICON))

####################################################################################################

def GetSeasonThumb(showName, seasonInt):
    '''retrieve the season thumbnail image from the Plex metadata database based on the title of the series'''
    seasonString = "season " + seasonInt
    #Log("Getting thumb for " + seasonString)
    tv_section_url = Get_PMS_URL() + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore')
    try:
        seasonListUrl = Get_PMS_URL() + tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('key')
        seasonListPage = HTML.ElementFromURL(seasonListUrl, errors='ignore')
        seasonThumb = seasonListPage.xpath('//directory[@index='+seasonInt+']')[0].get('thumb')
        data = HTTP.Request(Get_PMS_URL() + seasonThumb, cacheTime=CACHE_1MONTH).content
        return DataObject(data, 'image/jpeg')
    except:
        GetSeriesThumb(showName)

####################################################################################################

def GetTvSectionID():
    '''Determine what section(s) are TV series in Plex library'''
    
    library = HTML.ElementFromURL(Get_PMS_URL()+'/library/sections')
    sectionID = library.xpath('//directory[@type="show"]')[0].get('key')
    #Log('TV section ID: ' + sectionID)
    return sectionID
    
####################################################################################################

def GetSummary(showName):
    '''retrieve the series summary from the Plex metadata database based on the title of the series'''

    tv_section_url = Get_PMS_URL() + '/library/sections/' + TV_SECTION + '/all'
    tvLibrary = HTML.ElementFromURL(tv_section_url, errors='ignore', cacheTime=CACHE_1MONTH)
    try:
        summary = tvLibrary.xpath('//directory[@title="'+showName+'"]')[0].get('summary')
    except:
        summary = "Not found."
    
    return summary

####################################################################################################

def SeasonList(sender, showID, showName):
    '''Display a list of all season of the given TV series in SickBeard'''
    seasonListUrl = Get_SB_URL() + '/home/displayShow?show=' + showID
    dir = MediaContainer(ViewGroup='InfoList', title2=showName)
    listPage = HTML.ElementFromURL(seasonListUrl, errors='ignore')
    seasonList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    epCount = GetEpisodes(showID, 'all')
    #Log(epCount)
    dir.Append(Function(PopupDirectoryItem(SeasonSelectMenu, title='All Seasons', infoLabel=epCount, subtitle=showName,
        thumb=Function(GetSeriesThumb, showName=showName), showID=showID, showName=showName, seasonInt='all')))
    for season in seasonList.xpath('//input[@class="seasonCheck"]'):
        seasonNum = season.get('id')
        epCount = GetEpisodes(showID, seasonNum)
        #Log(epCount)
        dir.Append(Function(PopupDirectoryItem(SeasonSelectMenu, title='Season '+seasonNum, infoLabel=epCount,
            subtitle=showName, thumb=Function(GetSeasonThumb, showName=showName, seasonInt=seasonNum)),
            showID=showID, showName=showName, seasonNum=seasonNum))
    return dir

####################################################################################################

def SeasonSelectMenu(sender, showID, showName, seasonNum):
    '''display a popup menu with options for the selected season'''
    dir = MediaContainer(title='')
    dir.Append(Function(DirectoryItem(EpisodeList, title="View Episode List"), showID=showID,
        showName=showName, seasonInt=seasonNum))
    dir.Append(Function(DirectoryItem(MarkSeasonWanted, title="Mark all episodes as 'Wanted'"),
        showID=showID, seasonInt=seasonNum))
    
    return dir
    
####################################################################################################

def EpisodeList(sender, showID, showName, seasonInt):
    '''Display a list of all episodes of the given TV series including the SickBeard state of each'''
    episodeListUrl = Get_SB_URL() + '/home/displayShow?show=' + showID
    dir = MediaContainer(ViewGroup='InfoList', title2=showName, noCache=True)

    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore', cacheTime=0)
    episodeList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    for episode in episodeList.xpath('//tr'):
        if episode.get('class') == "seasonheader":
            pass
        elif episode.get('class') == None:
            pass
        elif seasonInt == 'all':
            # display all episodes for the series
            epNum = episode.xpath('.//a')[0].get('name')
            #Log('Found: Season ' + seasonInt + ' Episode' + epNum)
            epTitle = str(episode.xpath('./td')[4].text)[10:-10]
            #Log('Title: ' + epTitle)
            epDate = episode.xpath('./td')[5].text
            #Log('AirDate: ' + epDate)
            epFile = str(episode.xpath('./td')[6].text)[2:-7]
            #Log(epFile)
            epStatus = episode.xpath('./td')[7].text
            #Log('Status: ' + epStatus)
            dir.Append(Function(PopupDirectoryItem(EpisodeSelectMenu, title=epNum+' '+epTitle,
                infoLabel=epStatus, subtitle='Status: '+epStatus,
                summary="Airdate: "+epDate+"\nFileName: "+epFile,
                thumb=Function(GetSeriesThumb, showName=showName)), showID=showID, seasonNum=seasonInt,
                episodeNum=epNum))

        else:
            # display all episode for the given season of the given series
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
                #Log('Status: ' + epStatus)
                dir.Append(Function(PopupDirectoryItem(EpisodeSelectMenu, title=epNum+' '+epTitle,
                    infoLabel=epStatus, subtitle='Status: '+epStatus,
                    summary="Airdate: "+epDate+"\nFileName: "+epFile,
                    thumb=Function(GetSeriesThumb, showName=showName)), showID=showID, seasonNum=seasonInt,
                    episodeNum=epNum))
        
    return dir

####################################################################################################

def EditSeries(sender, showID, showName):
    '''display a menu of options for editing SickBeard functions for the given series'''
    
    cleanSlate = ResetGlobalQualityLists()
    
    dir = MediaContainer(ViewGroup='InfoList', title2='Edit '+showName, noCache=True)
    
    dir.Append(Function(PopupDirectoryItem(RescanFiles, 'Re-Scan Files', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID=showID))
    dir.Append(Function(PopupDirectoryItem(RenameEpisodes, 'Rename Episodes', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID))
    dir.Append(Function(PopupDirectoryItem(ForceFullUpdate, 'Force Full Update', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID))
    dir.Append(Function(PopupDirectoryItem(DeleteShow, 'Delete Series', subtitle='Series: '+ showName,
        thumb=R(ICON)), showID))
    
    seriesPrefs = GetSeriesPrefs(showID)
    
    if Client.Platform == ClientPlatform.iOS:
        dir.Append(Function(PopupDirectoryItem(SeriesQualityMenu, 'Quality Setting ['+seriesPrefs['qualityPreset']+']',
            subtitle='Series: '+ showName, thumb=R(ICON)), showID=showID, showName=showName))
    else:
        dir.Append(Function(PopupDirectoryItem(SeriesQualityMenu, 'Quality Setting', infoLabel=seriesPrefs['qualityPreset'], subtitle='Series: '+ showName,
            thumb=R(ICON)), showID=showID, showName=showName))
    
    if seriesPrefs['paused']:
        dir.Append(Function(DirectoryItem(UnpauseSeries, 'Unpause series', subtitle='Series: ' + showName,
        thumb=R(ICON)), showID=showID, showName=showName))
    else:
        dir.Append(Function(DirectoryItem(PauseSeries, 'Pause series', subtitle='Series: ' + showName,
        thumb=R(ICON)), showID=showID, showName=showName))
    
    if Client.Platform == ClientPlatform.iOS:
        if seriesPrefs['airByDate']:
            dir.Append(Function(DirectoryItem(AirByDate_Off, 'Air by Date [On]',
                subtitle='Series: '+showName, thumb=R(ICON)), showID=showID, showName=showName))
        else:
            dir.Append(Function(DirectoryItem(AirByDate_On, 'Air by Date [Off]', infoLabel='Off',
                subtitle='Series: '+showName, thumb=R(ICON)), showID=showID, showName=showName))
    else:
        if seriesPrefs['airByDate']:
            dir.Append(Function(DirectoryItem(AirByDate_Off, 'Air by Date', infoLabel='On',
                subtitle='Series: '+showName, thumb=R(ICON)), showID=showID, showName=showName))
        else:
            dir.Append(Function(DirectoryItem(AirByDate_On, 'Air by Date', infoLabel='Off',
                subtitle='Series: '+showName, thumb=R(ICON)), showID=showID, showName=showName))
    
    return dir

####################################################################################################

def ResetGlobalQualityLists():
    '''reset the global quality lists so that they don't carry over between editing different series'''
    try:
        Dict['anyQualities'] = []
        Dict['bestQualities'] = []
        return True
    except:
        return False

####################################################################################################

def ForceFullUpdate(sender, showID):
    '''tell SickBeard to do a force search for the given series'''
    updateUrl = Get_SB_URL() + '/home/updateShow?show=' + showID +'&force=1'
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Force search started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable force search'))

####################################################################################################

def RescanFiles(sender, showID):
    '''tell SickBeard to do re-scan files for the given series'''
    updateUrl = Get_SB_URL() + '/home/refreshShow?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Full file scan started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable to start file scan'))

####################################################################################################

def RenameEpisodes(sender, showID):
    '''tell SickBeard to do fix episode names for the given series'''
    updateUrl = Get_SB_URL() + '/home/fixEpisodeNames?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Episode renaming process started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable to start renaming process'))

####################################################################################################

def PauseSeries(sender, showID, showName):
    '''tell sickbeard to pause the given series'''
    seriesPrefs = GetSeriesPrefs(showID)
    #submit existing values as they are
    postValues = '&location=' + String.Quote(seriesPrefs['location'], usePlus=True).replace('/', '%2F') 
    for i in range(len(seriesPrefs['anyQualities'])):
        postValues = postValues + '&anyQualities=' + str(seriesPrefs['anyQualities'][i])
    for j in range(len(seriesPrefs['bestQualities'])):
        postValues = postValues + '&bestQualities=' + str(seriesPrefs['bestQualities'][j])
    if seriesPrefs['seasonFolders']:
        postValues = postValues + '&seasonfolders=on'
    #submit the value for 'pause'
    postValues = postValues + '&paused=on'
    #submit air_by_date as is
    if seriesPrefs['airByDate'] :
        postValues = postValues + '&air_by_date=on'
        
    url = Get_SB_URL() + '/home/editShow?show='+showID+postValues
    try:
        result = HTTP.Request(url, errors='ignore', cacheTime=0).content
    except:
        return MessageContainer('SickBeard', L('Series Pause command failed'))
    
    return MessageContainer('SickBeard', L(showName+' Paused.'))

####################################################################################################

def UnpauseSeries(sender, showID, showName):
    '''tell sickbeard to unpause the given series'''
    seriesPrefs = GetSeriesPrefs(showID)
    #submit existing values as they are
    postValues = '&location=' + String.Quote(seriesPrefs['location'], usePlus=True).replace('/', '%2F') 
    for i in range(len(seriesPrefs['anyQualities'])):
        postValues = postValues + '&anyQualities=' + str(seriesPrefs['anyQualities'][i])
    for j in range(len(seriesPrefs['bestQualities'])):
        postValues = postValues + '&bestQualities=' + str(seriesPrefs['bestQualities'][j])
    if seriesPrefs['seasonFolders']:
        postValues = postValues + '&seasonfolders=on'
    ###omit the value for 'pause'###
    #submit air_by_date as is
    if seriesPrefs['airByDate'] :
        postValues = postValues + '&air_by_date=on'
    
    url = Get_SB_URL() + '/home/editShow?show='+showID+postValues
    try:
        result = HTTP.Request(url, errors='ignore', cacheTime=0).content
    except:
        return MessageContainer('SickBeard', L('Series Unpause command failed'))
    
    return MessageContainer('SickBeard', L(showName+' Unpaused.'))
    
####################################################################################################

def AirByDate_On(sender, showID, showName):
    '''tell sickbeard to use air_by_date for the given series'''
    seriesPrefs = GetSeriesPrefs(showID)
    #submit existing values as they are
    postValues = '&location=' + String.Quote(seriesPrefs['location'], usePlus=True).replace('/', '%2F') 
    for i in range(len(seriesPrefs['anyQualities'])):
        postValues = postValues + '&anyQualities=' + str(seriesPrefs['anyQualities'][i])
    for j in range(len(seriesPrefs['bestQualities'])):
        postValues = postValues + '&bestQualities=' + str(seriesPrefs['bestQualities'][j])
    if seriesPrefs['seasonFolders']:
        postValues = postValues + '&seasonfolders=on'
    if seriesPrefs['paused']:
        postValues = postValues + '&paused=on'
    #submit air_by_date vale
    postValues = postValues + '&air_by_date=on'
        
    url = Get_SB_URL() + '/home/editShow?show='+showID+postValues
    try:
        result = HTTP.Request(url, errors='ignore', cacheTime=0).content
    except:
        return MessageContainer('SickBeard', L('"Air by date" command failed'))
    
    return MessageContainer('SickBeard', L(showName + '"Air by date" setting turned on.'))

####################################################################################################

def AirByDate_Off(sender, showID, showName):
    '''tell sickbeard not to use air_by_date for the given series'''
    seriesPrefs = GetSeriesPrefs(showID)
    #submit existing values as they are
    postValues = '&location=' + String.Quote(seriesPrefs['location'], usePlus=True).replace('/', '%2F') 
    for i in range(len(seriesPrefs['anyQualities'])):
        postValues = postValues + '&anyQualities=' + str(seriesPrefs['anyQualities'][i])
    for j in range(len(seriesPrefs['bestQualities'])):
        postValues = postValues + '&bestQualities=' + str(seriesPrefs['bestQualities'][j])
    if seriesPrefs['seasonFolders']:
        postValues = postValues + '&seasonfolders=on'
    if seriesPrefs['paused']:
        postValues = postValues + '&paused=on'
    ### omit value for air_by_date
    
    url = Get_SB_URL() + '/home/editShow?show='+showID+postValues
    try:
        result = HTTP.Request(url, errors='ignore', cacheTime=0).content
    except:
        return MessageContainer('SickBeard', L('Could not turn "Air by date" off.'))
    
    return MessageContainer('SickBeard', L(showName + '"Air by date" setting turned off.'))

####################################################################################################

def GetSeriesPrefs(showID):
    '''get the existing selections from the series edit page'''
    url = Get_SB_URL() + '/home/editShow?show=' + showID
    page = HTTP.Request(url, errors='ignore', cacheTime=0).content
    seriesPrefs = (page).replace('SELECTED', 'selected=True')
    seriesPrefs = (seriesPrefs).replace('CHECKED', 'checked=True')
    seriesPrefs = re.sub('(<option.*>)\n', '\1</option>', seriesPrefs)
    seriesPrefsPage = HTML.ElementFromString(seriesPrefs)
    location = seriesPrefsPage.xpath('//input[@name="location"]')[0].get('value')
    try:
        useSeasonFolders = seriesPrefsPage.xpath('//input[@name="seasonfolders"]')[0].get('checked')
        if useSeasonFolders == None:
            useSeasonFolders = False
    except:
        useSeasonFolders = False
    try:
        paused = seriesPrefsPage.xpath('//input[@name="paused"]')[0].get('checked')
        if paused == None:
            paused = False
    except:
        paused = False
    try:
        airByDate = seriesPrefsPage.xpath('//input[@name="air_by_date"]')[0].get('checked')
        if airByDate == None:
            airByDate = False
    except:
        airByDate = False
    qualityPreset = ''
    anyQualities = []
    bestQualities = []
    for option in seriesPrefsPage.xpath('//select[@id="qualityPreset"]/option'):
        if option.get('selected'):
            qualityPreset = option.get('value')
    for option in seriesPrefsPage.xpath('//select[@id="anyQualities"]/option'):
        if option.get('selected'):
            anyQualities.append(int(option.get('value')))
    for option in seriesPrefsPage.xpath('//select[@id="bestQualities"]/option'):
        if option.get('selected'):
            bestQualities.append(int(option.get('value')))
    
    ### convert qualityPreset value into a descriptive title ###
    if qualityPreset == '3':
        qualityPreset = 'SD'
    elif qualityPreset == '28':
        qualityPreset = 'HD'
    elif qualityPreset == '31':
        qualityPreset = 'Any'
    elif qualityPreset == '':
        if anyQualities == [1,4]:
            if bestQualities == [4]:
                qualityPreset = 'Best'
        else:
            qualityPreset = 'Custom'
    
    return {'location' : location, 'anyQualities' : anyQualities, 'qualityPreset' : qualityPreset,
            'bestQualities' : bestQualities, 'seasonFolders' : useSeasonFolders, 'paused' : paused,
            'airByDate' : airByDate}

####################################################################################################

def DeleteShow(sender, showID):
    '''tell SickBeard to do delete the given series'''
    updateUrl = Get_SB_URL() + '/home/deleteShow?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        return MessageContainer('SickBeard', L(showName + ' - Deleted from SickBeard database.'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable to delete series'))

####################################################################################################

def SeriesQualityMenu(sender, showID, showName):
    '''allow option to change quality setting for individual series'''
    dir = MediaContainer()
    
    ###Make sure that quality settings from editing another series are not carried over###
    cleanSlate = ResetGlobalQualityLists()
    
    dir.Append(Function(DirectoryItem(CustomQualitiesMenu, title='Custom', subtitle='Choose your own qualities',
        thumb=R(ICON)), showID=showID, showName=showName))
    dir.Append(Function(DirectoryItem(ChangeSeriesQuality, title='SD', subtitle='SD TV/SD DVD',
        thumb=R(ICON)), showID=showID, showName=showName, qualityPreset='SD'))
    dir.Append(Function(DirectoryItem(ChangeSeriesQuality, title='HD', subtitle='HD TV/720p WEB-DL/720p BluRay',
        thumb=R(ICON)), showID=showID, showName=showName, qualityPreset='HD'))
    dir.Append(Function(DirectoryItem(ChangeSeriesQuality, title='Any', subtitle='SD TV/SD DVD/HD TV/720p WEB-DL/720p BluRay',
        thumb=R(ICON)), showID=showID, showName=showName, qualityPreset='Any'))
    dir.Append(Function(DirectoryItem(ChangeSeriesQuality, title='Best', subtitle='SD TV/HD TV replace with HD TV',
        thumb=R(ICON)), showID=showID, showName=showName, qualityPreset='Best'))
    
    return dir
    
####################################################################################################    

def ChangeSeriesQuality(sender, showID, showName, qualityPreset):
    '''submit a change in quality for the given series'''
       
    seriesPrefs = GetSeriesPrefs(showID)
    
    if qualityPreset == 'SD':
        seriesPrefs['anyQualities'] = [1,2]
        seriesPrefs['bestQualites'] = []
    elif qualityPreset == 'HD':
        seriesPrefs['anyQualities'] = [4,8,16]
        seriesPrefs['bestQualites'] = []
    elif qualityPreset == 'Any':
        seriesPrefs['anyQualities'] = [1,2,4,8,16]
        seriesPrefs['bestQualites'] = []
    elif qualityPreset == 'Custom':
        seriesPrefs['anyQualities'] = Dict['anyQualities']
        seriesPrefs['bestQualities'] = Dict['bestQualities']
        
    #Log(seriesPrefs['anyQualities'])
    #Log(seriesPrefs['bestQualities'])
    #submit new values for quality
    postValues = '&location=' + String.Quote(seriesPrefs['location'], usePlus=True).replace('/', '%2F') 
    for i in range(len(seriesPrefs['anyQualities'])):
        postValues = postValues + '&anyQualities=' + str(seriesPrefs['anyQualities'][i])
    for j in range(len(seriesPrefs['bestQualities'])):
        postValues = postValues + '&bestQualities=' + str(seriesPrefs['bestQualities'][j])
    
    #submit existing values as they are
    if seriesPrefs['seasonFolders']:
        postValues = postValues + '&seasonfolders=on'
    if seriesPrefs['paused']:
        postValues = postValues + '&paused=on'
    if seriesPrefs['airByDate'] :
        postValues = postValues + '&air_by_date=on'
        
    url = Get_SB_URL() + '/home/editShow?show='+showID+postValues
    
    try:
        result = HTTP.Request(url, errors='ignore', cacheTime=0).content
    except:
        return MessageContainer('SickBeard', L('Failed to change quality settings.'))
    
    cleanSlate = ResetGlobalQualityLists()
    
    return MessageContainer('SickBeard', L('Changes applied to ' + showName))

####################################################################################################

def CustomQualitiesMenu(sender, showID, showName):
    '''allow selection of user defined quality settings'''
    
    dir = MediaContainer(ViewGroup='InfoList', title2='Custom Quality for: '+showName)
    
    dir.Append(Function(DirectoryItem(InitialQualityMenu, title='Initial Download Quality',
        summary="If I don't have the episode then tell SickBeard to download it in ONE of the selected qualities",
        thumb=R(ICON)), showID=showID, showName=showName))
    dir.Append(Function(DirectoryItem(ReplacementQualityMenu, title='Replacement Download Quality',
        summary='Tell SickBeard to re-download the episodes in any or all of these qualities as they are available',
        thumb=R(ICON)), showID=showID, showName=showName))
    dir.Append(Function(DirectoryItem(ChangeSeriesQuality, title='Submit custom quality changes',
        summary='Changes to custom quality settings will not be saved until you submit them by clicking here.',
        thumb=R(ICON)), showID=showID, showName=showName, qualityPreset='Custom'))
    
    return dir

####################################################################################################

def InitialQualityMenu(sender, showID, showName):
    '''Tell SickBeard which quality/qualities to download as soon as they are available'''
    
    dir = MediaContainer(ViewGroup='InfoList', title2='Intial Quality: ' + showName, noCache=True)
    
    seriesPrefs = GetSeriesPrefs(showID)
    anyQualities = seriesPrefs['anyQualities']
    tempList = Dict['anyQualities']
    #Log(tempList)
    
    try:
        if anyQualities != tempList:
            #Log('templist differs')
            if tempList != []:
                anyQualities = tempList
    except:
        #Log('Failed try!')
        pass
    
    Dict['anyQualities'] = anyQualities
    
    #Log(anyQualities)
    
    if 1 in anyQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='SD TV', infoLabel='Selected', thumb=R(ICON)),
            value=1, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='SD TV', thumb=R(ICON)), value=1, list='initial'))
    if 2 in anyQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='SD DVD', infoLabel='Selected', thumb=R(ICON)),
            value=2, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='SD DVD', thumb=R(ICON)), value=2, list='initial'))
    if 4 in anyQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='HD TV', infoLabel='Selected', thumb=R(ICON)),
            value=4, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='HD TV', thumb=R(ICON)), value=4, list='initial'))
    if 8 in anyQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='720p WEB-DL', infoLabel='Selected', thumb=R(ICON)),
            value=8, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='720p WEB-DL', thumb=R(ICON)), value=8, list='initial'))
    if 16 in anyQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='720p BluRay', infoLabel='Selected', thumb=R(ICON)),
            value=16, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='720p BluRay', thumb=R(ICON)), value=16, list='initial'))
    if 32 in anyQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='1080p BluRay', infoLabel='Selected', thumb=R(ICON)),
            value=32, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='1080p BluRay', thumb=R(ICON)), value=32, list='initial'))
    
    return dir

####################################################################################################

def ReplacementQualityMenu(sender, showID, showName):
    '''Tell SickBeard to which quality/qualities to download as replacements for lower intial
        quality downloads as they are available'''
        
    dir = MediaContainer(ViewGroup='InfoList', title2='Replacement Quality: '+showName, noCache=True)
    
    seriesPrefs = GetSeriesPrefs(showID)
    bestQualities = seriesPrefs['bestQualities']
    tempList = Dict['anyQualities']
    #Log(tempList)
    
    try:
        if bestQualities != tempList:
            #Log('templist differs')
            if tempList != []:
                bestQualities = tempList
    except:
        #Log('Failed try!')
        pass
    
    Dict['bestQualities'] = bestQualities
    
    #Log(bestQualities)
    
    if 2 in bestQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='SD DVD', infoLabel='Selected', thumb=R(ICON)),
            value=2, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='SD DVD', thumb=R(ICON)), value=2, list='initial'))
    if 4 in bestQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='HD TV', infoLabel='Selected', thumb=R(ICON)),
            value=4, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='HD TV', thumb=R(ICON)), value=4, list='initial'))
    if 8 in bestQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='720p WEB-DL', infoLabel='Selected', thumb=R(ICON)),
            value=8, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='720p WEB-DL', thumb=R(ICON)), value=8, list='initial'))
    if 16 in bestQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='720p BluRay', infoLabel='Selected', thumb=R(ICON)),
            value=16, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='720p BluRay', thumb=R(ICON)), value=16, list='initial'))
    if 32 in bestQualities:
        dir.Append(Function(DirectoryItem(RemoveFromList, title='1080p BluRay', infoLabel='Selected', thumb=R(ICON)),
            value=32, list='initial'))
    else:
        dir.Append(Function(DirectoryItem(AddToList, title='1080p BluRay', thumb=R(ICON)), value=32, list='initial'))
    
    return dir

####################################################################################################

def EpisodeRefresh(sender, url="", showID="", seasonNum="", episodeNum=""):
    '''tell SickBeard to do a force search for the given episode'''
    if url != "":
        updateUrl = Get_SB_URL() + url
        #Log(updateUrl)
    elif showID != "":
        updateUrl = Get_SB_URL() + '/home/searchEpisode?show='+showID+'&season='+seasonNum+'&episode='+episodeNum
    else:
        return MessageContainer('SickBeard Plugin', L('Episode never aired. Cannot force search.'))
    
    try:
        updating = HTTP.Request(updateUrl, errors='ignore').content
        #Log(updating)
        return MessageContainer('SickBeard Plugin', L('Force search started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable force search'))

####################################################################################################

def MarkEpisodeWanted(sender, showID, seasonNum, episodeNum):
    '''tell SickBeard to do mark the given episode as "wanted"'''
    
    url = Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+seasonNum+'x'+episodeNum+'&status=3'
    
    try:
        result = HTTP.Request(url, errors='ignore').content
        return MessageContainer('SickBeard Plugin', L('Episode marked as wanted'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable mark as wanted'))

####################################################################################################

def MarkSeasonWanted(sender, showID, seasonInt):
    '''iterate through the given season and tell SickBeard to mark each episode as wanted'''
    
    #url = Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+epNum+'&status=3'
    
    episodeListUrl = Get_SB_URL() + '/home/displayShow?show=' + showID
    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore', cacheTime=0)
    episodeList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    episodesMarked = 0
    for episode in episodeList.xpath('//tr'):
        if episode.get('class') == "seasonheader":
            pass
        elif episode.get('class') == None:
            pass
        elif seasonInt == 'all':
            epNum = episode.xpath('.//a')[0].get('name')
            try:
                result = HTTP.Request(Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+epNum+'&status=3', errors='ignore').content
                #Log('Episode: '+epNum+' marked as "Wanted"')
                episodesMarked += 1
            except:
                #Log('Failed: Unable to mark episode '+epNum+' as "Wanted"')
                pass
        else:
            # count all episode for the given season of the given series
            epNum = episode.xpath('.//a')[0].get('name')
            if str(epNum)[0:len(str(seasonInt))] == seasonInt:
                try:
                    result = HTTP.Request(Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+epNum+'&status=3', errors='ignore').content
                    #Log('Episode: '+epNum+' marked as "Wanted"')
                    episodesMarked += 1
                except:
                    #Log('Failed: Unable to mark episode '+epNum+' as "Wanted"')
                    pass
    
    return MessageContainer('SickBeard Plugin', L(str(episodesMarked)+' marked as "Wanted"'))

####################################################################################################

def GetEpisodes(showID, seasonInt):
    '''determine the number of downloaded (or snatched) episodes out of the total number of episodes
        for the given season of the given series'''
    
    episodeListUrl = Get_SB_URL() + '/home/displayShow?show=' + showID
    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore', cacheTime=0)
    episodeList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    allEpisodes = 0
    haveEpisodes = 0
    for episode in episodeList.xpath('//tr'):
        if episode.get('class') == "seasonheader":
            pass
        elif episode.get('class') == None:
            pass
        elif seasonInt == 'all':
            # count all episodes for the given series
            epNum = episode.xpath('.//a')[0].get('name')
            epStatus = episode.xpath('./td')[7].text
            #Log(epStatus)
            if epStatus == 'Skipped':
                allEpisodes += 1
            elif epStatus == 'Unaired':
                allEpisodes += 1
            elif epStatus == 'Wanted':
                allEpisodes += 1
            else:
                allEpisodes += 1
                haveEpisodes += 1
        else:
            # count all episode for the given season of the given series
            epNum = episode.xpath('.//a')[0].get('name')
            if str(epNum)[0:len(str(seasonInt))] == seasonInt:
                epNum = str(epNum)[(len(str(seasonInt))+1):]
                epStatus = episode.xpath('./td')[7].text
                #Log('Status: ' + epStatus)
                if epStatus == 'Skipped':
                    allEpisodes += 1
                elif epStatus == 'Unaired':
                    allEpisodes += 1
                elif epStatus == 'Wanted':
                    allEpisodes += 1
                else:
                    allEpisodes += 1
                    haveEpisodes += 1
         
        
    epCount = str(haveEpisodes)+'/'+str(allEpisodes)
    return epCount

####################################################################################################

def Get_SB_URL():
    return 'http://'+Prefs['sbIP']+':'+Prefs['sbPort']
    
####################################################################################################

def Get_PMS_URL():
    return 'http://'+Prefs['plexIP']+':32400'
    
####################################################################################################

def RemoveFromList(sender, value, list):
    
    tempList = []
    
    if list == 'initial':
        tempList = Dict['anyQualities']
        tempList.remove(value)
        Dict['anyQualities'] = tempList
    elif list == 'replacement':
        tempList = Dict['bestQualities']
        tempList.remove(value)
        Dict['bestQualities'] = tempList
    else:
        pass
    
    return True

####################################################################################################

def AddToList(sender, value, list):
    
    tempList = []
    
    if list == 'initial':
        tempList = Dict['anyQualities']
        tempList.append(value)
        tempList.sort()
        Dict['anyQualities'] = tempList
    elif list == 'replacement':
        tempList = Dict['bestQualities']
        tempList.append(value)
        tempList.sort()
        Dict['bestQualities'] = tempList
    else:
        pass
    
    return True

####################################################################################################

def Restart(): ###Remove this once HTTP.SetPassword doesn't require restart###
    '''trick the plugin into restarting by "modifying" a file in the bundle'''
    user = os.getlogin()
    file = 'Users/'+user+'/Library/Application Support/Plex Media Server/Plug-ins/SickBeard.bundle/Contents/Code/__init__.py'
    temp = os.open(file, os.O_RDWR)
    string = os.read(temp, 5000)
    startOver = os.lseek(temp,0,0)
    temp3 = os.write(temp, string)
    Log('Restarting plug-in')
    
    return MessageContainer(NAME, L('Restarting plugin for changes to take effect.'))

####################################################################################################

def CheckForUpdate():
    '''check if sickbeard can be updated'''
    url = Get_SB_URL() + '/home'
    page = HTML.ElementFromURL(url, errors='ignore', cacheTime=0)
    try:
        updateCheck = page.xpath('//div[@class="message ui-state-highlight ui-corner-all"]/p/a')[1]
        link = updateCheck.get('href')    
        Log('Update available: '+link)
        return {'available':True, 'link':link}
    except:
        Log('No update available.')
        return {'available':False, 'link':None}

####################################################################################################

def UpdateSB(sender, link):
    url = Get_SB_URL() + link
    update = HTTP.Request(url, errors='ignore').content
    #sleep(30)
    #restartSB = subprocess.Popen('launchctl start com.sickbeard.sickbeard', shell=True)
    return MessageContainer(NAME, L('SickBeard update started.'))
    
####################################################################################################

#def RecentlyViewedMenu(sender):
#    '''retrieve list of recently viewed episodes and allow option to tell Sickbeard to mark them as
#    archived and then delete the files (on an individual basis)'''
#    Log('Test')
#    dir = MediaContainer(viewGroup='InfoList', noCache=True)
#    
#    showIDs = {}
#    showList = HTML.ElementFromURL(Get_SB_URL()+'/home', errors='ignore', cacheTime=0)
#    for show in showList.xpath('//tr[@class="evenLine"]'):
#        #try:
#        tvdbID = show.xpath('.//a')[0].get('href').split('=')[1]
#        Log(tvdbID)
#        showName = show.xpath('.//a')[0].text
#        showIDs = showIDs.list() + {showName:tvdbID}
#    #    except:
#    #        pass
#    
#    recentlyViewedUrl = Get_PMS_URL() + '/library/sections/' + TV_SECTION + '/recentlyViewed'
#    recentlyViewed = HTML.ElementFromURL(recentlyViewedUrl, cacheTime=0)
#    
#    for episode in recentlyViewed.xpath('//video'):
#        showName = episode.get('grandparenttitle')
#        Log(showName)
#        episodeTitle = episode.get('title')
#        Log(episodeTitle)
#        epSummary = episode.get('summary')
#        Log(epSummary)
#        seasonNumber = episode.get('parentindex')
#        Log(seasonNumber)
#        episodeNumber = episode.get('index')
#        Log(episodeNumber)
#        file = episode.xpath('.//part')[0].get('file')
#        tvdbID = showIDs[showName]
#        dir.Append(Function(PopupDirectoryItem(ArchiveAndDelete, title=showName+': S'+seasonNumber+'E'+episodeNumber,
#            subtitle=episodeTitle, summary = epSummary, thumb=GetEpisodeThumb(episode.get('thumb')),
#            tvdbID=tvdbID, season=seasonNumber, episode=episodeNumber, file=file)))
#    
#    return dir
#
####################################################################################################

#def GetEpisodeThumb(sender, link):
#    try:
#        data = HTTP.Request(Get_PMS_URL() + link, cacheTime=CACHE_1MONTH).content
#        return DataObject(data, 'image/jpeg')
#    except:
#        return R(ICON)

####################################################################################################

#def ArchiveAndDelete(sender, tvdbID, season, episode, file):
#    return