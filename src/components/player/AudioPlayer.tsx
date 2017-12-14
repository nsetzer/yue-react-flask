
import * as React from 'react';
import PropTypes from 'prop-types';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Sound from 'react-sound';

import Button from 'material-ui/Button';

import * as actionCreators from '../../actions/queue';
import PlayArrow from 'material-ui-icons/PlayArrow';
import Pause from 'material-ui-icons/Pause';
import SkipNext from 'material-ui-icons/SkipNext';
import SkipPrevious from 'material-ui-icons/SkipPrevious';
import VolumeUp from 'material-ui-icons/VolumeUp';
import VolumeDown from 'material-ui-icons/VolumeDown';
import VolumeMute from 'material-ui-icons/VolumeMute';

import IconButton from 'material-ui/IconButton';

import Grid from 'material-ui/Grid';

import {
  fmtDuration,
} from '../../utils/misc'

export interface ProgressBarProps {
  position: number, // seconds
  duration: number,
  setPosition: (number) => any,
}

export interface ProgressBarState {
}

const LargeIconStyle = {
    width: "48px",
    height: "48px",
}

const MediumIconStyle = {
    width: "32px",
    height: "32px",
}

const ProgressOuterStyle = {
    width: "100%",
    height: "10px",
    //overflow: "hidden",
    cursor: "pointer",
    backgroundColor: "black",
    borderRadius: "5px",

}

const ProgressInnerStyle = {
    height: "100%",
    width: "50%",
    backgroundColor: "red",
    borderRadius: "5px",

}

const TextContainer: React.CSSProperties = {
    height:"100%",
    width:"100%",
    position:"relative",
}

const TextBottomLeftStyle: React.CSSProperties = {
    bottom: "0px",
    left: "0px",
    padding: "0px",
    margin: "auto",
    position:"absolute",
}

const TextBottomRightStyle: React.CSSProperties = {
    bottom: "0px",
    right: "0px",
    padding: "0px",
    margin: "auto",
    position:"absolute",
}

const TextVerticalCenterStyle: React.CSSProperties = {
    display: "flex",
    aligmItems: "center",
    justifyContent: "center",
}

const VolumeIconCenterStyle: React.CSSProperties = {
    right: "0px",
    position:"absolute",
    height:"32px",
    width:"32px",
    margin: "auto"
}

const VolumeBarCenterStyle: React.CSSProperties = {
    top: "11px",
    position:"absolute",
    height:"100%",
    width:"100%",
    margin: "auto"
}

class ProgressBar extends React.Component<ProgressBarProps, ProgressBarState> {

    constructor(props) {
        super(props);
        //this.state = {}
        this.onClick = this.onClick.bind(this)
    }

    onClick(e) {

        const xPos = (e.pageX - e.currentTarget.getBoundingClientRect().left) / e.currentTarget.offsetWidth;

        this.props.setPosition(xPos * this.props.duration)

    }

    render() {

        let p = 100 * this.props.position / this.props.duration;
        ProgressInnerStyle.width = p + "%"
        let innerStyle = Object.assign({}, ProgressInnerStyle, {width: `${p}%`});

        return (
          <div style={ProgressOuterStyle} onClick={this.onClick}>
            <div style={innerStyle}/>
          </div>
        );
    }
}

export interface AudioPlayerProps {
  url: string,
  artist: string,
  title: string,
  nextSong: (boolean) => any,
  previousSong: () => any,
  iconColor: string,
}

export interface AudioPlayerState {
  status: any,
  set_position: number,
  position: number,
  duration: number,
  volume: number,
}


class AudioPlayer extends React.Component<AudioPlayerProps,AudioPlayerState> {

  constructor(props) {
    super(props);
    this.state = {status:Sound.status.PAUSED,
                  set_position: 0,
                  position:0,
                  duration:120,
                  volume: 50}
    this.play = this.play.bind(this)
    this.pause = this.pause.bind(this)
    this.playPause = this.playPause.bind(this)
    this.onPlaying = this.onPlaying.bind(this)
    this.onLoading = this.onLoading.bind(this)
    this.onFinishedPlaying = this.onFinishedPlaying.bind(this)
    this.onSetPosition = this.onSetPosition.bind(this)
    this.onSetVolume = this.onSetVolume.bind(this)
    this.onClickNext = this.onClickNext.bind(this)
    this.onClickPrevious = this.onClickPrevious.bind(this)
  }

  play() {
    this.setState({status:Sound.status.PLAYING});
  }

  pause() {
    this.setState({status:Sound.status.PAUSED});
  }

  playPause() {
    if (this.state.status == Sound.status.PAUSED) {
      this.setState({status:Sound.status.PLAYING});
    } else {
      this.setState({status:Sound.status.PAUSED});
    }
  }

  onPlaying(o) {
    //console.log(o)
    this.setState({
        position: o.position,
        duration: o.duration,
    });
  }

  onLoading(o) {
    //console.log(o)
  }

  onFinishedPlaying() {
    this.props.nextSong(true)
  }

  onSetPosition(s) {
    this.setState({set_position: s});
  }

  onSetVolume(v) {
    if (v < 3) {
        v = 0
    } else if (v > 97) {
        v = 100
    }
    this.setState({volume: v});
  }

  onClickNext() {
    this.props.nextSong(false)
  }

  onClickPrevious() {
    this.props.previousSong()
  }

  render() {
    /*https://www.materialui.co/colors*/
    let iconColor = this.props.iconColor;
    let volumeIcon = <VolumeUp style={MediumIconStyle} color={iconColor}/>
    if (this.state.volume == 0) {
        volumeIcon = <VolumeMute style={MediumIconStyle} color={iconColor}/>
    } else if (this.state.volume < 50) {
        volumeIcon = <VolumeDown style={MediumIconStyle} color={iconColor}/>
    }

    return <div>

      {/*https://www.npmjs.com/package/react-sound*/}


          <b>{this.props.title}</b>
          <br/>
          {this.props.artist}

          <Grid container spacing={24}>

            <Grid item xs={2}>
                <div style={TextContainer}>
                <div style={TextBottomLeftStyle}>
                    {fmtDuration(Math.round(this.state.position/1000))}
                </div>
                </div>
            </Grid>

            <Grid item xs={8}>
                <div style={TextContainer}>
                <div style={TextVerticalCenterStyle}>
                    <IconButton onClick={(e) => this.onClickPrevious()}>
                      <SkipPrevious style={MediumIconStyle} color={iconColor}/>
                    </IconButton>

                    <IconButton onClick={(e) => this.playPause()}>
                    {(this.state.status == Sound.status.PAUSED)?
                      <PlayArrow style={LargeIconStyle} color={iconColor}/>:
                      <Pause style={LargeIconStyle} color={iconColor}/>}
                    </IconButton>

                    <IconButton onClick={(e) => this.onClickNext()}>
                      <SkipNext style={MediumIconStyle} color={iconColor}/>
                    </IconButton>
                </div>
                </div>
            </Grid>

            <Grid item xs={2}>
               <div style={TextContainer}>
               <div style={TextBottomRightStyle}>
                 {fmtDuration(Math.round(this.state.duration/1000))}
               </div>
               </div>

            </Grid>

            </Grid>

            <ProgressBar position={this.state.position}
                         duration={this.state.duration}
                         setPosition={this.onSetPosition}/>

            <Grid container spacing={8} style={{height:"40px"}}>
            <Grid item xs={3}>
                <div style={TextContainer}>
                <div style={VolumeIconCenterStyle}>
                    {volumeIcon}
                </div>
                </div>
            </Grid>
            <Grid item xs={6}>
                <div style={TextContainer}>
                <div style={VolumeBarCenterStyle}>

                <ProgressBar position={this.state.volume}
                             duration={100}
                             setPosition={this.onSetVolume}/>
                </div>
                </div>
            </Grid>
            <Grid item xs={3}>
            </Grid>
            </Grid>

            <Sound
        url={this.props.url}
        volume={this.state.volume}
        playStatus={this.state.status}
        onPlaying={this.onPlaying}
        onLoading={this.onLoading}
        onFinishedPlaying={this.onFinishedPlaying}
        playFromPosition={this.state.set_position}
      />
      </div>;
  }
}

export default AudioPlayer


