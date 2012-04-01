''' http://172.16.1.125:8081/api/d613672d430777f73b2bc2a1c9d44b32/?cmd=show.addnew&help=1 '''

import re, os, subprocess, string
from base64 import b64encode

####################################################################################################

APPLICATION_PREFIX = "/applications/sickbeard"

NAME = 'SickBeard'

ART         = 'art-default.jpg'
ICON        = 'icon-default.png'
SEARCH_ICON = 'icon-search.png'
PREFS_ICON  = 'icon-prefs.png'

####################################################################################################

def Start():
    
    Plugin.AddPrefixHandler(APPLICATION_PREFIX, MainMenu, L('SickBeard'), ICON, ART)

    if Dict['DefaultSettings'] == None:
        Dict['DefaultSettings'] = {'tvdbLang' : '', 'whichSeries' : '', 'rootDir' : '', 'defaultStatus' : '3',  'seasonFolders' : 'on', 'anyQualities' : 'HD', 'skipShow' : ''}
    if Dict['CustomSettings'] == None:
        Dict['CustomSettings'] = {'tvdbLang' : '', 'whichSeries' : '', 'rootDir' : '', 'defaultStatus' : '',  'seasonFolders' : '', 'anyQualities' : '', 'skipShow' : ''}
    
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    DirectoryObject.thumb = R(ICON)
    PopupDirectoryObject.thumb = R(ICON)
    HTTP.CacheTime=3600*3
     
    
####################################################################################################

def AuthHeader():
    header = {}

    if Prefs['sbUser'] and Prefs['sbPass']:
        header = {'Authorization': 'Basic ' + b64encode(Prefs['sbUser'] + ':' + Prefs['sbPass'])}

    return header

####################################################################################################

def MainMenu():
    oc = ObjectContainer(view_group="InfoList")
    
    oc.add(DirectoryObject(key=Callback(Future), title="Coming Episodes",
        summary="See which shows that you follow have episodes airing soon"))
    oc.add(DirectoryObject(key=Callback(ShowList), title="All Shows",
        summary="See details about all shows which SickBeard manages for you"))
    oc.add(SearchDirectoryObject(key=Callback(Search), title="Add Show", summary="Add show(s) to SickBeard by searching ",
        prompt="Search TVDB for...", thumb=R(ICON)))
    #dir.Append(PrefsItem(title="Preferences",subtitle="SickBeard plugin prefs",
    #    summary="Set SickBeard plugin preferences to allow it to connect to SickBeard app",thumb=R(PREFS_ICON)))
    
    
    #updateValues = CheckForUpdate()
    #if updateValues['available']:
    #    dir.Append(Function(PopupDirectoryItem(UpdateSB, 'SickBeard Update Available',
    #        'May require you to restart SickBeard', 'Depending on your set-up, you may need to restart' +
    #        ' SickBeard after updating.', thumb=R(ICON)), link = updateValues['link']))

    return oc

####################################################################################################

def Future():
    
    oc = ObjectContainer(view_group='InfoList', title2='Coming Episodes')
    
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="missed"), title="Missed Episodes",
        summary="Episodes which aired prior to today's date."))
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="today"), title="Airing Today",
        summary="Episodes which are scheduled to air today."))
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="soon"), title="Airing Soon",
        summary="Episodes which are scheduled to air this week."))
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="later"), title="Airing Later",
        summary="Episodes which are scheduled to air after this week."))
    
    return oc
        
####################################################################################################

def ComingEpisodes(timeframe=""):
    
    oc = ObjectContainer(view_group='InfoList', title1='Coming Episodes', title2=str.capitalize(timeframe), no_cache=True)
    
    coming_Eps = API_Request([{'key':'cmd', 'value':'future'}])
    
    for episode in coming_Eps['data'][timeframe]:
        title = EpisodeTitle(episode)
        summary = EpisodeSummary(episode)
        oc.add(PopupDirectoryObject(key=Callback(EpisodePopup, episode=episode),
            title=title, summary=summary, thumb=Callback(GetThumb, tvdbID=episode['tvdbid']))) 
       
    return oc

####################################################################################################

def Search(query):
    
    oc = ObjectContainer(view_group="InfoList", title2="TVDB Results", no_cache=True)
    
    search_results = API_Request([{'key':'cmd', 'value':'sb.searchtvdb'},{'key':'name', 'value':String.Quote(query, usePlus=True)}])
    
    for result in search_results['data']['results']:
        oc.add(PopupDirectoryObject(
            key=Callback(AddShowMenu, show=result),
            title = result['name'],
            summary = "TVDB ID: %s\nFirst Aired: %s" % (result['tvdbid'], result['first_aired']),
            thumb = Callback(GetThumb, tvdbID=result['tvdbid'])))
    
    return oc
    
####################################################################################################  

def ShowList():
    '''List all shows that SickBeard manages, and relevant info about each show'''
    
    oc = ObjectContainer(view_group="InfoList", title2="All Shows", no_cache=True)
    
    shows = API_Request([{'key':'cmd', 'value':'shows'},{'key':'sort', 'value':'name'}])['data']
    
    for (key, value) in shows.items():
        tvdbid = key
        show = value
        
        if show['paused']:
            paused = "True"
        else:
            paused = "False"
        ###TODO(?) Re-add episode counts?###
        title = show['show_name']
        summary = "Next Episode: %s\nNetwork: %s\nDownload Quality: %s\nStatus: %s\nPaused: %s" % (
            show['next_ep_airdate'], show['network'], show['quality'], show['status'], paused, )
            
        oc.add(PopupDirectoryObject(key=Callback(SeriesPopup, tvdbid=tvdbid), title=title, summary=summary,
            thumb=Callback(GetThumb, tvdbID=episode['tvdbid'])))
        
    return oc
    
####################################################################################################

def SeriesPopup(tvdbid):
    '''display a popup menu with the option to force a search for the selected series'''
    oc = ObjectContainer()
    
    oc.add(DirectoryObject(key=Callback(SeasonList, tvdbid=tvdbid), title="View Season List"))
    oc.add(DirectoryObject(key=Callback(EditSeries, tvdbid=tvdbid), title="Edit SickBeard series options"))
    
    return oc
    
####################################################################################################

def EpisodePopup(episode={}):
    '''display a popup menu with the option to force a search for the selected episode/series'''
    oc = ObjectContainer()
    
    oc.add(DirectoryObject(key=Callback(EpisodeRefresh, episode=episode), title="Force search for this episode"))
    oc.add(DirectoryObject(key=Callback(EpisodeSetStatus, episode=episode),  title="Mark this episode as wanted"))
    
    return oc

####################################################################################################

def AddShowMenu(show={}):
    '''offer the option to add the given show to sickbeard with default settings or with custom settings'''
    
    oc = ObjectContainer()
    
    oc.add(DirectoryObject(key=Callback(AddShow, tvdbID=result['tvdbid']), title="Add with default settings"))
    oc.add(DirectoryObject(key=Callback(CustomAddShow, tvdbID=result['tvdbid']), title="Add with custom settings"))
    
    return oc
    
####################################################################################################

def AddShow(tvdbID, settings=[]):
    '''add the given show to the SickBeard database with the given settings,
        or use SickBeard's default settings if settings == []'''
    
    params = [{"key":"cmd", "value":"show.addnew"}]
    for param in settings:
        params.append(param)
        
    message = API_Request(params)

    return ObjectContainer(header=NAME, message=message)
    
####################################################################################################

def CustomAddShow(tvdbID):
    '''retrieve the user's default settings from SickBeard and use them as a starting point to allow
        modifications before adding a show with custom settings'''
    
    oc = MediaContainer(title2="Add Show Settings...", no_cache=True)
    
    GetSickBeardDefaults()
    GetSickBeardRootDirs()
    
    '''Offer separate menu options for each default setting'''
    oc.add(PopupDirectoryObject(key=Callback(QualitySetting, type="initial"), title="Initial Quality", summary=Dict['DefaultSettings']['initial']))
    oc.add(PopupDirectoryObject(key=Callback(QualitySetting, type="archive"), title="Archive Quality", summary=Dict['DefaultSettings']['initial']))
    oc.add(PopupDirectoryObject(key=Callback(LanguageSetting), title="TVDB Language: [%s]" % Dict['DefaultSettings']['lang']))
    oc.add(PopupDirectoryObject(key=Callback(StatusSetting), title="Status of previous episodes: [%s]" % Dict['DefaultSettings']['status']))
    if Dict['DefaultSettings']['season_folders'] == 1:
        season_folders = "True"
    else:
        season_folders = "False"
    oc.add(PopupDirectoryObject(key=Callback(SeasonFolderSetting), title="Use season Folders", summary=season_folders))
    
    oc.add(DirectoryObject(key=Callback(AddShow, tvdbID=tvdbID), title="Add show with these settings"))
    
    return oc

####################################################################################################

def GetSickBeardDefaults():
    default_settings = API_Request([{"key":"cmd", "value":"sb.getdefaults"}])
    for key, value in default_settings['data']:
        Dict['DefaultSettings'][key] = value
        
    Dict['DefaultSettings']['lang'] = Prefs['TVDBLang']
    
    return
    
####################################################################################################

def GetSickBeardRootDirs():
    Dict['RootDirs'] = API_Request([{"key":"cmd", "value":"sb.getrootdirs"}])['data']
    return

####################################################################################################

def QualitySetting(type):
    oc = ObjectContainer(title2="%s Quality" % string.capitalize(type), no_cache=True)
    for quality in API_Request([{"key":"cmd", "value":"sb.addnew"},{"key":"help", "value":"1"}])['data'][type]['allowedValues']:
        if quality in Dict['DefaultSettings'][type]:
            oc.add(DirectoryObject(key=Callback(ChangeQualities, quality=quality, type=type, action="remove"), title = "[*] %s" % quality))
        else:
            oc.add(DirectoryObject(key=Callback(ChangeQualities, quality=quality, type=type, action="add"), title = "[ ] %s" % quality))
    return oc

####################################################################################################

def ChangeQualities(quality, type, action):
    qualities = Dict['DefaultSettings'][type]
    if action == "remove":
        qualities.remove(quality)
    elif action == "add":
        qualities.append(quality)
    else:
        pass
    Dict['DefaultSettings'][type] = qualities
    Dict.Save()
    return

####################################################################################################

def LanguageSetting():
    oc = ObjectContainer(title2="tvdb Language", no_cache=True)
    for lang in API_Request([{"key":"cmd", "value":"sb.addnew"},{"key":"help", "value":"1"}])['data']['lang']['allowedValues']:
        if lang in Dict['DefaultSettings']['lang']:
            oc.add(DirectoryObject(key=Callback(ChangeLanguage, lang=lang, value="True"), title = "[*] %s" % lang))
        else:
            oc.add(DirectoryObject(key=Callback(ChangeLanguage, lang=lang, value="False"), title = "[ ] %s" % lang))
    return oc
    
####################################################################################################

def ChangeLanguage(lang, value):
    if value == "True":
        Dict['DefaultSettings']['lang'] = lang
    else:
        Dict['DefaultSettings']['lang'] = ''
    Dict.Save()
    return

####################################################################################################

def StatusSetting():
    oc = ObjectContainer(title2="Status", no_cache=True)
    for status in API_Request([{"key":"cmd", "value":"sb.addnew"},{"key":"help", "value":"1"}])['data']['status']['allowedValues']:
        if status in Dict['DefaultSettings']['status']:
            oc.add(DirectoryObject(key=Callback(ChangeStatus, status=status, value="True"), title = "[*] %s" % status))
        else:
            oc.add(DirectoryObject(key=Callback(ChangeStatus, status=status, value="False"), title = "[ ] %s" % status))
    return oc

####################################################################################################

def ChangeStatus(status, value):
    if value == "True":
        Dict['DefaultSettings']['status'] = status
    else:
        Dict['DefaultSettings']['status'] = ''
    Dict.Save()
    return

####################################################################################################

def SeasonFolderSetting():
    oc = ObjectContainer(title2="Status", no_cache=True)
    for option in API_Request([{"key":"cmd", "value":"sb.addnew"},{"key":"help", "value":"1"}])['data']['season_folder']['allowedValues']:
        if option:
            label = "Yes"
        else:
            label = "No"
        if option in Dict['DefaultSettings']['season_folder']:
            oc.add(DirectoryObject(key=Callback(ChangeSeasonFolder, option=option, value="True"), title = "[*] %s" % label))
        else:
            oc.add(DirectoryObject(key=Callback(ChangeSeasonFolder, option=option, value="False"), title = "[ ] %s" % label))
    return oc
    
####################################################################################################

def ChangeSeasonFolder(option, value):
    if value == "True":
        Dict['DefaultSettings']['season_folder'] = option
    else:
        Dict['DefaultSettings']['season_folder'] = ''
    Dict.Save()
    return

####################################################################################################

def SeasonList(sender, showID, showName):
    '''Display a list of all season of the given TV series in SickBeard'''
    seasonListUrl = Get_SB_URL() + '/home/displayShow?show=' + showID
    if Client.Platform == ClientPlatform.iOS:
        dir = MediaContainer(viewGroup='List', title2=showName)
    else:
        dir = MediaContainer(viewGroup='InfoList', title2=showName)
    listPage = HTML.ElementFromURL(seasonListUrl, errors='ignore', headers=AuthHeader())
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
    dir = MediaContainer(viewGroup='InfoList', title2=showName, noCache=True)

    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore', cacheTime=0, headers=AuthHeader())
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
            epTitle = episode.xpath('./td')[4].text.strip()
            #Log('Title: ' + epTitle)
            epDate = episode.xpath('./td')[5].text
            #Log('AirDate: ' + epDate)
            epFile = episode.xpath('./td')[6].text.strip()
            if epFile != '':
                if str(Prefs['tvDir'])[-1] == '/':
                    filePath = Prefs['tvDir']+'%s/%s' % (showName, epFile)
                else:
                    filePath = Prefs['tvDir']+'/%s/%s' % (showName, epFile)
            else:
                filePath = ''
            #Log(filePath)
            epStatus = episode.xpath('./td')[7].text
            #Log('Status: ' + epStatus)
            dir.Append(Function(PopupDirectoryItem(EpisodeSelectMenu, title=epNum+' '+epTitle,
                infoLabel=epStatus, subtitle='Status: '+epStatus,
                summary="Airdate: "+epDate+"\nFileName: "+filePath,
                thumb=Function(GetSeriesThumb, showName=showName)), showID=showID, seasonNum=seasonInt,
                episodeNum=epNum, file=filePath))

        else:
            # display all episode for the given season of the given series
            try:
                epNum = episode.xpath('.//input[@type="checkbox"]')[0].get('id')
                #Log(epNum)
            except:
                #Log('epNum not found')
                continue
            ### Need to make changes here so that series with more than 9 seasons list episodes properly
            try:
                nextDigit=epNum[len(str(seasonInt))]
                #Log('nextDigit='+nextDigit)
            except:
                nextDigit='-1'
                #Log('nextDigit='+nextDigit)
            #Log('Character at position '+ epNum[len(str(seasonInt))] + ' is ' + nextDigit)
            if nextDigit in ['0','1','2','3','4','5','6','7','8','9']:
                #ignore season with more digits than what we're searching for
                continue
            else:
                if str(epNum)[0:len(str(seasonInt))] == seasonInt:
                    epNum = str(epNum)[(len(str(seasonInt))+1):]
                    #Log('Found: Season ' + seasonInt + ' Episode' + epNum)
                    epTitle = episode.xpath('./td')[4].text.strip()
                    #Log('Title: ' + epTitle)
                    epDate = episode.xpath('./td')[5].text
                    #Log('AirDate: ' + epDate)
                    epFile = episode.xpath('./td')[6].text.strip()
                    if epFile != '':
                        if not Prefs['tvDir']:
                            filePath = '%s/%s' % (showName, epFile)
                        elif str(Prefs['tvDir'])[-1] == '/':
                            filePath = Prefs['tvDir']+'%s/%s' % (showName, epFile)
                        else:
                            filePath = Prefs['tvDir']+'/%s/%s' % (showName, epFile)
                    else:
                        filePath = ''
                    #Log(filePath)
                    #Log(epFile)
                    epStatus = episode.xpath('./td')[7].text
                    #Log('Status: ' + epStatus)
                    dir.Append(Function(PopupDirectoryItem(EpisodeSelectMenu, title=epNum+' '+epTitle,
                        infoLabel=epStatus, subtitle='Status: '+epStatus,
                        summary="Airdate: "+epDate+"\nFileName: "+filePath,
                        thumb=Function(GetSeriesThumb, showName=showName)), showID=showID, seasonNum=seasonInt,
                        episodeNum=epNum, file=filePath))
        
    return dir

####################################################################################################

def EditSeries(sender, showID, showName):
    '''display a menu of options for editing SickBeard functions for the given series'''
    
    cleanSlate = ResetGlobalQualityLists()
    
    dir = MediaContainer(viewGroup='InfoList', title2='Edit '+showName, noCache=True)
    
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
        updating = HTTP.Request(updateUrl, errors='ignore', headers=AuthHeader()).content
        return MessageContainer('SickBeard Plugin', L('Force search started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable force search'))

####################################################################################################

def RescanFiles(sender, showID):
    '''tell SickBeard to do re-scan files for the given series'''
    updateUrl = Get_SB_URL() + '/home/refreshShow?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore', headers=AuthHeader()).content
        return MessageContainer('SickBeard Plugin', L('Full file scan started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable to start file scan'))

####################################################################################################

def RenameEpisodes(sender, showID):
    '''tell SickBeard to do fix episode names for the given series'''
    updateUrl = Get_SB_URL() + '/home/fixEpisodeNames?show=' + showID
    #Log(updateUrl)
    try:
        updating = HTTP.Request(updateUrl, errors='ignore', headers=AuthHeader()).content
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
        result = HTTP.Request(url, errors='ignore', cacheTime=0, headers=AuthHeader()).content
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
        result = HTTP.Request(url, errors='ignore', cacheTime=0, headers=AuthHeader()).content
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
        result = HTTP.Request(url, errors='ignore', cacheTime=0, headers=AuthHeader()).content
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
        result = HTTP.Request(url, errors='ignore', cacheTime=0, headers=AuthHeader()).content
    except:
        return MessageContainer('SickBeard', L('Could not turn "Air by date" off.'))
    
    return MessageContainer('SickBeard', L(showName + '"Air by date" setting turned off.'))

####################################################################################################

def GetSeriesPrefs(showID):
    '''get the existing selections from the series edit page'''
    url = Get_SB_URL() + '/home/editShow?show=' + showID
    page = HTTP.Request(url, errors='ignore', cacheTime=0, headers=AuthHeader()).content
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
        updating = HTTP.Request(updateUrl, errors='ignore', headers=AuthHeader()).content
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
        result = HTTP.Request(url, errors='ignore', cacheTime=0, headers=AuthHeader()).content
    except:
        return MessageContainer('SickBeard', L('Failed to change quality settings.'))
    
    cleanSlate = ResetGlobalQualityLists()
    
    return MessageContainer('SickBeard', L('Changes applied to ' + showName))

####################################################################################################

def CustomQualitiesMenu(sender, showID, showName):
    '''allow selection of user defined quality settings'''
    
    dir = MediaContainer(viewGroup='InfoList', title2='Custom Quality for: '+showName)
    
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
    
    dir = MediaContainer(viewGroup='InfoList', title2='Intial Quality: ' + showName, noCache=True)
    
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
        
    dir = MediaContainer(viewGroup='InfoList', title2='Replacement Quality: '+showName, noCache=True)
    
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
        updating = HTTP.Request(updateUrl, errors='ignore', headers=AuthHeader()).content
        #Log(updating)
        return MessageContainer('SickBeard Plugin', L('Force search started'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable force search'))

####################################################################################################
###def EpisodeSetStatus(episode={})
###'''Present a menu with options to change the wanted/skipped/archived/ignored status of the given episode'''
def MarkEpisodeWanted(sender, showID, seasonNum, episodeNum):
    '''tell SickBeard to do mark the given episode as "wanted"'''
    
    url = Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+seasonNum+'x'+episodeNum+'&status=3'
    
    try:
        result = HTTP.Request(url, errors='ignore', headers=AuthHeader()).content
        return MessageContainer('SickBeard Plugin', L('Episode marked as wanted'))
    except:
        return MessageContainer('SickBeard Plugin', L('Error - unable mark as wanted'))

####################################################################################################

def MarkSeasonWanted(sender, showID, seasonInt):
    '''iterate through the given season and tell SickBeard to mark each episode as wanted'''
    
    #url = Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+epNum+'&status=3'
    
    episodeListUrl = Get_SB_URL() + '/home/displayShow?show=' + showID
    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore', cacheTime=0, headers=AuthHeader())
    episodeList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    episodesMarked = 0
    for episode in episodeList.xpath('//tr'):
        if episode.get('class') == "seasonheader":
            pass
        elif episode.get('class') == None:
            pass
        elif seasonInt == 'all':
            params = episode.xpath('.//a')[0].get('href').split('&')
            #Log(params)
            epNum = -1
            seasonNum = -1
            for param in params:
                #Log(param)
                if param[:7] == 'episode':
                    epNum = param.split('=')[1]
                elif param[:6] == 'season':
                    seasonNum = param.split('=')[1]
            #epNum = episode.xpath('.//a')[0].get('name')
            #Log('Episode: '+str(epNum))
            #Log('Season: '+str(seasonNum))
            try:
                result = HTTP.Request(Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+seasonNum+'x'+epNum+'&status=3', errors='ignore', cacheTime=0, headers=AuthHeader()).content
                Log('Episode: '+seasonNum+'x'+epNum+' marked as "Wanted"')
                episodesMarked += 1
            except:
                Log('Failed: Unable to mark episode '+seasonNum+'x'+epNum+' as "Wanted"')
                pass
        elif len(episode.xpath('.//a')) > 0:
            # count all episode for the given season of the given series
            params = episode.xpath('.//a')[0].get('href').split('&')
            #Log(params)
            epNum = -1
            seasonNum = -1
            for param in params:
                #Log(param)
                if param[:7] == 'episode':
                    epNum = param.split('=')[1]
                elif param[:6] == 'season':
                    seasonNum = param.split('=')[1]
            #epNum = episode.xpath('.//a')[0].get('name')
            #Log('Episode: '+str(epNum))
            #Log('Season: '+str(seasonNum))
            if str(seasonNum)[0:len(str(seasonInt))] == seasonInt:
                try:
                    result = HTTP.Request(Get_SB_URL() + '/home/setStatus?show='+showID+'&eps='+seasonNum+'x'+epNum+'&status=3', errors='ignore', cacheTime=0, headers=AuthHeader()).content
                    Log('Episode: '+seasonNum+'x'+epNum+' marked as "Wanted"')
                    episodesMarked += 1
                except:
                    Log('Failed: Unable to mark episode '+seasonNum+'x'+epNum+' as "Wanted"')
                    pass
        else:
            pass
    
    return MessageContainer('SickBeard Plugin', L(str(episodesMarked)+' marked as "Wanted"'))

####################################################################################################

def GetEpisodes(showID, seasonInt):
    '''determine the number of downloaded (or snatched) episodes out of the total number of episodes
        for the given season of the given series'''
    
    episodeListUrl = Get_SB_URL() + '/home/displayShow?show=' + showID
    listPage = HTML.ElementFromURL(episodeListUrl, errors='ignore', cacheTime=0, headers=AuthHeader())
    episodeList = listPage.xpath('//table[@class="sickbeardTable"]')[0]
    allEpisodes = 0
    haveEpisodes = 0
    for episode in episodeList.xpath('//tr'):
        #Log(episode.get('class'))
        if episode.get('class') == "seasonheader":
            pass
        elif episode.get('class') == None:
            pass
        elif seasonInt == 'all':
            # count all episodes for the given series
            try:
                epNum = episode.xpath('.//input[@type="checkbox"]')[0].get('id')
                #Log(epNum)
            except:
                #Log('epNum not found')
                continue
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
            try: epNum = episode.xpath('.//input[@type="checkbox"]')[0].get('id')
            except: continue
            try:
                nextDigit=epNum[len(str(seasonInt))]
                #Log('epNum = %s and seasonInt = %s' % (epNum, seasonInt))
                #Log('nextDigit='+nextDigit)
                #Log('Character at position %s is %s' % (len(str(seasonInt)), nextDigit))
                if nextDigit in ['0','1','2','3','4','5','6','7','8','9']:
                    #ignore season with more digits than what we're searching for
                    #Log('ignore me')
                    continue
                else:
                    #Log('Take a closer look')
                    if str(epNum)[0:len(str(seasonInt))] == seasonInt:
                        #Log('Count me')
                        epNum = str(epNum)[(len(str(seasonInt))):]
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
            except:
                continue

        
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

def CheckForUpdate():
    '''check if sickbeard can be updated'''
    url = Get_SB_URL() + '/home'
    try:
        page = HTML.ElementFromURL(url, errors='ignore', cacheTime=0, headers=AuthHeader())
        updateCheck = page.xpath('//div[@id="upgrade-notification"]/div/span/a')[1]
        link = updateCheck.get('href')
        #Log('Update available: '+link)
        return {'available':True, 'link':link}
    except:
        #Log('No update available.')
        return {'available':False, 'link':None}

####################################################################################################

def UpdateSB(sender, link):
    url = Get_SB_URL() + link
    try:
        update = HTTP.Request(url, errors='ignore', headers=AuthHeader()).content
    except:
        pass
    restartSB = subprocess.Popen('launchctl start com.sickbeard.sickbeard', shell=True)
    return MessageContainer(NAME, L('SickBeard update started.'))
    
####################################################################################################

def API_URL():
    '''build and return the base url for all SickBeard API requests'''
    return 'http://%s:%s/api/%s/?' % (Prefs['sbIP'], Prefs['sbPort'], Dict['SB_API_Key'])
    
####################################################################################################

def Get_API_Key():
    '''scrape the SickBeard/Config/General page for the API key and set it in the plugin Dict[]'''
    url = Get_SB_URL() + '/config/general'
    page = HTML.ElementFromURL(url)
    Dict['SB_API_Key'] = page.xpath('//input[@name="api_key"]')[0].get('value')
    return

####################################################################################################

def API_Request(params=[]):
    '''use the given args to make an API request and return the JSON'''
    
    '''start with the base API url'''
    request_url = API_URL
    '''build the request rl with the given parameters'''
    for i in len(params):
        request_url = request_url + params[i-1]['key'] + '=' + params[i-1]['value'] + '&'
    '''strip the trailing "&" from the request_url'''
    request_url = request_url.strip('&')
    '''send the request and confirm success'''
    data = JSON.ObjectFromURL(request_url)
    if data['result'] == "success":
        return data
    else:
        return ObjectContainer(header=NAME, message="The API request: %s\n was unsuccessful. Please try again." % request_url)
    
####################################################################################################

def EpisodeTitle(episode={}):
    '''build a string for the episode's title using the show name, season #, episode #, and episode title'''
    episode_title = "%s - S%sE%s - %s" % (episode['show_name'], episode['season'], episode['episode'], episode['ep_name'])
    return episode_title
    
####################################################################################################

def EpisodeSummary(episode={}):
    '''build a string for the episode's summary using the episode's airdate, airs, network, paused(if true), quality, show_status,
        and ep_plot'''
    if episode['paused']:
        paused = 'Paused: True\n'
    else:
        paused = ''
    episode_summary = "Episode Airdate: %s\nTimeslot: %s\nNetwork: %s\nQuality: %s\nStatus: %s\n%s\nSynopsis: %s" % (
        episode['airdate'], episode['airs'], episode['network'], episode['quality'], episode['show_status'], paused, episode['ep_plot'])
    return episode_summary
    
####################################################################################################

def GetThumb(tvdbID):
    thumb_url = API_URL + "cmd=show.getposter&tvdbid=%s" % tvdbID
    data = HTTP.Request(thumb_url).content
    return DataObject(data, 'image/jpeg')