
import * as React from 'react';
import PropTypes from 'prop-types';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Sound from 'react-sound';

import Button from 'material-ui/Button';

import * as actionCreators from '../actions/queue';
import PlayArrow from 'material-ui-icons/PlayArrow';
import Pause from 'material-ui-icons/Pause';
import SkipNext from 'material-ui-icons/SkipNext';
import SkipPrevious from 'material-ui-icons/SkipPrevious';
import IconButton from 'material-ui/IconButton';

import Grid from 'material-ui/Grid';

import {
  fmtDuration,
} from '../utils/misc'

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

const TextVerticalCenterStyle:React.CSSProperties = {
    display: "flex",
    aligmItems: "center",
    justifyContent: "center",
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


export interface SoundProps {
  url: string,
  artist: string,
  title: string,
}

export interface SoundState {
  status: any,
  set_position: number,
  position: number,
  duration: number,
}



//https://www.npmjs.com/package/react-sound
class SoundView extends React.Component<SoundProps,SoundState> {

  constructor(props) {
    super(props);
    this.state = {status:Sound.status.PAUSED,
                  set_position: 0,
                  position:0,
                  duration:120}
    this.play = this.play.bind(this)
    this.pause = this.pause.bind(this)
    this.playPause = this.playPause.bind(this)
    this.onPlaying = this.onPlaying.bind(this)
    this.onLoading = this.onLoading.bind(this)
    this.onFinishedPlaying = this.onFinishedPlaying.bind(this)
    this.onSetPosition = this.onSetPosition.bind(this)
  }

  play() {
    console.log("play" + this.props.url)
    this.setState({status:Sound.status.PLAYING});
  }

  pause() {
    console.log("play")
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
    console.log("playback finished")
  }

  onSetPosition(s) {
    this.setState({set_position: s});
  }

  render() {
    /*https://www.materialui.co/colors*/
    return <div>


      <h2>{this.props.title}</h2>
      <h3>{this.props.artist}</h3>

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
              <IconButton >
                <SkipPrevious style={MediumIconStyle} color="#607D8B"/>
              </IconButton>

              <IconButton onClick={(e) => this.playPause()}>
              {(this.state.status == Sound.status.PAUSED)?
                <PlayArrow style={LargeIconStyle} color="#607D8B"/>:
                <Pause style={LargeIconStyle} color="#607D8B"/>}
              </IconButton>

              <IconButton >
                <SkipNext style={MediumIconStyle} color="#607D8B"/>
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
      <Sound
              url={this.props.url}
              playStatus={this.state.status}
              onPlaying={this.onPlaying}
              onLoading={this.onLoading}
              onFinishedPlaying={this.onFinishedPlaying}
              playFromPosition={this.state.set_position}
      />
      </div>;
  }
}

function mapStateToProps(state) {
  return {
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}
export default SoundView

/*connect(
  mapStateToProps,
  mapDispatchToProps
)(SoundView);*/
