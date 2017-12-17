import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import { withTheme } from 'material-ui/styles';

import Grid from 'material-ui/Grid';

import * as actionCreators from '../../actions/queue';
import AudioPlayer from "./AudioPlayer"

import IconButton from 'material-ui/IconButton';
import * as _MenuIcon from 'material-ui-icons/Menu';
const MenuIcon = _MenuIcon.default

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../../utils/misc'

const MediumIconStyle = {
    width: "32px",
    height: "32px",
}

export interface SoundViewProps {
  queueStatus: string;
  songs: Array<any>;
  song_history: Array<any>;
  getQueue: () => any;
  populateQueue: () => any;
  nextSongInQueue: PropTypes.func;
  previousSongInQueue: PropTypes.func;
  showMenuIcon: boolean;
  openMenu: () => any;
  theme: any;
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

    const { theme } = this.props;
    let iconColor = theme.palette.text.primary;

    return (
      <div style={{paddingLeft:10,
                   paddingRight:10,
                   paddingTop:5,
                   paddingBottom: 5}}>
        <div style={{position:"absolute",
                     left: 5,
                     top: 5}}>
        {this.props.showMenuIcon?
                <IconButton aria-label="Menu"
                            onClick={this.props.openMenu}>
                    <MenuIcon style={MediumIconStyle} color={iconColor}/>
                </IconButton>:null}
        </div>


          <Grid container spacing={24} justify="center">
            <Grid item  xs={12} sm={6} md={6}>
              <div style={{textAlign:"center"}}>
              <AudioPlayer
                url={this.state.audioUrl}
                artist={currentArtist}
                title={currentTitle}
                nextSong={this.onSongNext}
                previousSong={this.onSongPrevious}
                iconColor={iconColor}
              />
              </div>
            </Grid>
          </Grid>
      </div>


    );
  }
}

function mapStateToProps(state, ownProps) {
  return {
      queueStatus: state.queue.statusText,
      songs: state.queue.songs,
      song_history: state.queue.history,
      showMenuIcon: ownProps.showMenuIcon,
      openMenu: ownProps.openMenu,
      theme: ownProps.theme,
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

// TODO: withTheme does not work with this class...
export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SoundView);
