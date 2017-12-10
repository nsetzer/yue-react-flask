import * as React from 'react';
import PropTypes from 'prop-types';
//import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

const logo = require('../svg/logo.svg');
import './App.css';

import Button from 'material-ui/Button';

import * as actionCreators from '../actions/queue';

import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction
import IconButton from 'material-ui/IconButton';
import Send from 'material-ui-icons/Send';
import Delete from 'material-ui-icons/Delete';

import SoundView from "./SoundView"

import Grid from 'material-ui/Grid';

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../utils/misc'

export interface MainViewProps {
  logoutAndRedirect: PropTypes.func,
  userName: PropTypes.string,
  queueStatus: string,
  songs: Array<any>,
  history: Array<any>,
  getQueue: () => any,
  populateQueue: () => any,
  nextSongInQueue: PropTypes.func,
  previousSongInQueue: PropTypes.func,
};

export interface MainViewState {
  open: boolean,
  audioUrl: string,
  currentSong: {id: string, artist: string, title: string},
}

const listRightStyle = {
   textAlign: "right",
};


class MainView extends React.Component<MainViewProps,MainViewState> {

  constructor(props) {
    super(props);
    this.state = {open:true, audioUrl: "", currentSong: null};
    this.logout = this.logout.bind(this)
    this.onSongNext = this.onSongNext.bind(this)
    this.onSongPrevious = this.onSongPrevious.bind(this)
    this.componentWillReceiveProps = this.componentWillReceiveProps.bind(this)
  }

  componentDidMount() {
    this.props.getQueue();
  }

  componentWillReceiveProps(nextProps) {
    let audioUrl = (nextProps.songs && nextProps.songs.length>0)?
                    getSongAudioUrl(nextProps.songs[0]):null
    let song = (nextProps.songs && nextProps.songs.length>0)?
                    nextProps.songs[0]:null
    this.setState({
          audioUrl: audioUrl,
          currentSong: song
      });
    console.log("new song received")
  }

  logout(e) {
      e.preventDefault();
      this.props.logoutAndRedirect(this.props);
      this.setState({
          open: false,
      });
  }

  onSongNext(auto) {
    // auto: true if the song completed normally
    this.props.nextSongInQueue(this.props.songs)
  }

  onSongPrevious() {
    this.props.previousSongInQueue(this.props.history, this.props.songs)
  }

  render() {
    let currentSong = this.state.currentSong;
    let currentArtist = (currentSong)?currentSong.artist:"";
    let currentTitle = (currentSong)?currentSong.title:"";
    return (
      <div>
      <div className="App">
        <header className="App-header">

        <Grid container spacing={24}>

        <Grid item sm={3} md={4}>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <SoundView
            url={this.state.audioUrl}
            artist={currentArtist}
            title={currentTitle}
            nextSong={this.onSongNext}
            previousSong={this.onSongPrevious}
          />
        </Grid>

        <Grid item sm={3} md={4}>
        <Button
          style={{ marginTop: 50 }}
          onClick={(e) => this.logout(e)}
          raised={true}
        >Logout</Button>
        </Grid>

        </Grid>

        </header>
        <br/>



      </div>

      <IconButton aria-label="Populate"
         onClick={() => {this.props.populateQueue()}}>
          <Send />
      </IconButton>

        <List>
        {
          (this.props.songs && this.props.songs.length>0) ?
            this.props.songs.map( (song) => {
              return <ListItem key={song.id}>
                       <ListItemText primary={song.title}
                                     secondary={song.artist}/>
                       <ListItemText style={listRightStyle} primary={fmtDuration(song.length)}/>
                       <ListItemSecondaryAction>
                         <IconButton aria-label="Delete"
                                     onClick={() => {}}>
                          <Delete />
                         </IconButton>
                       </ListItemSecondaryAction>
                     </ListItem>
            }) : <div>No Songs To Display</div>
        }
        </List>

      </div>
    );
  }
}



function mapStateToProps(state) {
  return {
      queueStatus: state.queue.statusText,
      songs: state.queue.songs,
      history: state.queue.history,
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(MainView);
