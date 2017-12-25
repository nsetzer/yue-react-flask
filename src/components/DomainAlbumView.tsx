
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import Button from 'material-ui/Button';

import Grid from 'material-ui/Grid';

import * as UiCard from 'material-ui/Card';
const Card = UiCard.default

import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction
import IconButton from 'material-ui/IconButton';
import Send from 'material-ui-icons/Send';
import MoreVert from 'material-ui-icons/MoreVert';
import NavigateBefore from 'material-ui-icons/NavigateBefore';
import Menu, { MenuItem } from 'material-ui/Menu';

import * as libraryActionCreators from '../actions/library';
import * as queueActionCreators from '../actions/queue';
const actionCreators = Object.assign({},
                                     libraryActionCreators,
                                     queueActionCreators);
import History from '../history'

import Typography from 'material-ui/Typography';

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../utils/misc'

export interface IMenuOpts {
  open: boolean,
  anchorEl: any,
  index: number,
  song: any
}

export interface IDomainAlbumViewProps {
  match: any
  libraryStatus: string,
  libraryGetArtistSongs: (a) => any,
  libraryGetAlbumSongs: (a,b) => any,
  search_results: Array<any>,
  insertNextInQueue: (s) => any
  createQueue: (q,m) => any,
};

export interface IDomainAlbumViewState {
  menuOpts: IMenuOpts
}

const listRightStyle = {
   textAlign: "right",
};

const MediumIconStyle = {
    width: "32px",
    height: "32px",
}

function navigateTo(url) {
  History.push(url)
  window.scrollTo(0,0)
}

function navigateBack() {
  History.goBack()
  window.scrollTo(0,0)
}

class DomainAlbumView extends React.Component<IDomainAlbumViewProps,IDomainAlbumViewState> {

  constructor(props) {
    super(props);
    this.state = {menuOpts:{open:false, anchorEl:null, song: null, index: -1}}
    this.componentDidMount = this.componentDidMount.bind(this)
    this.onOpenMenu = this.onOpenMenu.bind(this)
    this.onMenuClose = this.onMenuClose.bind(this)
    this.onQueueSong = this.onQueueSong.bind(this)
  }

  public componentDidMount() {

    let artist = this.props.match.params.artist
    let album = this.props.match.params.album

    if (album == "$all") {
      this.props.libraryGetArtistSongs(artist);
    } else {
      this.props.libraryGetAlbumSongs(artist, album);
    }

  }

  public onOpenMenu(event, index, song) {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = true;
    menuOpts.anchorEl = event.currentTarget
    menuOpts.index = index
    menuOpts.song = song
    this.setState({menuOpts: menuOpts});
  }

  public onMenuClose() {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
  }

  /*
  componentWillReceiveProps(nextProps) {
    let audioUrl = (nextProps.songs && nextProps.songs.length>0)?
                    getSongAudioUrl(nextProps.songs[0]):null
    let song = (nextProps.songs && nextProps.songs.length>0)?
                    nextProps.songs[0]:null
    this.setState({
          audioUrl: audioUrl,
          currentSong: song
      });
  }*/

  public onQueueSong() {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
    this.props.insertNextInQueue([ menuOpts.song, ])
  }

  public render() {
    let artist_name = this.props.match.params.artist
    let this_album = this.props.match.params.album;
    let default_query=`artist="${artist_name}" && album="${this_album}"`
    if (this_album==='$all') {
      this_album = 'All Songs'
      default_query=`artist="${artist_name}"`
    }

    return (
        <div>
        <Grid container spacing={24} justify="center">
            <Grid item  xs={2}>
              <IconButton onClick={(e) => navigateBack()}>
                <NavigateBefore style={MediumIconStyle} />
              </IconButton>
            </Grid>
            <Grid item  xs={8}>
            <Typography type="title" align="center" gutterBottom noWrap>
              {this.props.match.params.artist}<br/>
              {this_album}
            </Typography>
            </Grid>
            <Grid item  xs={2}>
            <IconButton onClick={(e) => {}}>
                <MoreVert style={MediumIconStyle} />
              </IconButton>
            </Grid>
        </Grid>

        <Button
          raised
          color="accent"
          onClick={(e) => {
            this.props.createQueue(default_query, 'random')}
        }>
          Random Play All
        </Button>

        <List>
            {
              (this.props.search_results && this.props.search_results.length>0) ?
                this.props.search_results.map( (song, index) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                                key={song.id}>
                           <ListItem>
                             <ListItemText primary={song.title}
                                           secondary={song.artist + " - " + song.album}/>
                             <ListItemText style={listRightStyle} primary={fmtDuration(song.length)}/>
                             <ListItemSecondaryAction>
                               <IconButton aria-label="Delete"
                                           onClick={(e) => {this.onOpenMenu(e,index,song)}}>
                                <MoreVert />
                               </IconButton>
                             </ListItemSecondaryAction>
                           </ListItem>
                         </Card>
                }) : <div>No Songs To Display</div>
            }
         </List>

         <Menu
          id="simple-menu"
          anchorEl={this.state.menuOpts.anchorEl}
          open={this.state.menuOpts.open}
          onRequestClose={this.onMenuClose}>
          <MenuItem onClick={this.onQueueSong}>Queue Song</MenuItem>
        </Menu>

        </div>
    )
  }
}
function mapStateToProps(state) {
  return {
      libraryStatus: state.library.statusText,
      search_results: state.library.search_results
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(DomainAlbumView);
