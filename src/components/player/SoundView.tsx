import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Grid from 'material-ui/Grid';

import * as actionCreators from '../../actions/queue';
import AudioPlayer from "./AudioPlayer"

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../../utils/misc'

export interface SoundViewProps {
  queueStatus: string,
  songs: Array<any>,
  song_history: Array<any>,
  getQueue: () => any,
  populateQueue: () => any,
  nextSongInQueue: PropTypes.func,
  previousSongInQueue: PropTypes.func,
}

export interface SoundViewState {
  audioUrl: string,
  currentSong: {id: string, artist: string, title: string},
}

class SoundView extends React.Component<SoundViewProps,SoundViewState> {

  constructor(props) {
    super(props);
    this.state = {audioUrl: "",
                  currentSong: null};
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

  onSongNext(auto) {
    // auto: true if the song completed normally
    this.props.nextSongInQueue()
  }

  onSongPrevious() {
    this.props.previousSongInQueue()
  }

  render() {
    let currentSong = this.state.currentSong;
    let currentArtist = (currentSong)?currentSong.artist:"";
    let currentTitle = (currentSong)?currentSong.title:"";

    return (
      <Grid container spacing={24}>

          <Grid item sm={3} md={4}>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <AudioPlayer
              url={this.state.audioUrl}
              artist={currentArtist}
              title={currentTitle}
              nextSong={this.onSongNext}
              previousSong={this.onSongPrevious}
            />
          </Grid>

          <Grid item sm={3} md={4}>
          </Grid>

          </Grid>


    );
  }
}

function mapStateToProps(state) {
  return {
      queueStatus: state.queue.statusText,
      songs: state.queue.songs,
      song_history: state.queue.history,
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SoundView);
