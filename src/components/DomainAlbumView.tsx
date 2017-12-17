
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import Button from 'material-ui/Button';

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

import * as actionCreators from '../actions/library';

import History from '../history'

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../utils/misc'

export interface DomainAlbumViewProps {
  match: any
  libraryStatus: string,
  libraryGetArtistSongs: (a) => any,
  libraryGetAlbumSongs: (a,b) => any,
  search_results: Array<any>,
};

export interface DomainAlbumViewState {
}

const listRightStyle = {
   textAlign: "right",
};


class DomainAlbumView extends React.Component<DomainAlbumViewProps,DomainAlbumViewState> {

  constructor(props) {
    super(props);
    this.componentDidMount = this.componentDidMount.bind(this)
  }

  componentDidMount() {

    // TODO: this query only needs to run once, find a better
    // way to gate that behavior
    let artist = this.props.match.params.artist
    let album = this.props.match.params.album

    if (album == "$all") {
      this.props.libraryGetArtistSongs(artist);
    } else {
      this.props.libraryGetAlbumSongs(artist, album);
    }
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

  render() {

    console.log(this.props.search_results)
    console.log(window.location)

    return (
        <div>
        <IconButton onClick={(e) => History.goBack()}>
          <NavigateBefore />
        </IconButton>

        <h2>{this.props.match.params.artist} - {this.props.match.params.album}</h2>

        <List>
            {
              (this.props.search_results && this.props.search_results.length>0) ?
                this.props.search_results.map( (song) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}>
                           <ListItem key={song.id}>
                             <ListItemText primary={song.title}
                                           secondary={song.artist}/>
                             <ListItemText style={listRightStyle} primary={fmtDuration(song.length)}/>
                             <ListItemSecondaryAction>
                               <IconButton aria-label="Delete"
                                           onClick={() => {}}>
                                <MoreVert />
                               </IconButton>
                             </ListItemSecondaryAction>
                           </ListItem>
                         </Card>
                }) : <div>No Songs To Display</div>
            }
         </List>

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