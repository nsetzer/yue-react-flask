
import * as React from 'react';
import PropTypes from 'prop-types';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Sound from 'react-sound';

import Button from 'material-ui/Button';

import * as actionCreators from '../actions/queue';

export interface SoundProps {
  url: string,
}

export interface SoundState {
  status: any,
}

//https://www.npmjs.com/package/react-sound
class SoundView extends React.Component<SoundProps,SoundState> {

  constructor(props) {
    super(props);
    this.state = {status:Sound.status.PAUSED}
    this.play = this.play.bind(this)
    this.pause = this.pause.bind(this)
    this.playPause = this.playPause.bind(this)
    this.onPlaying = this.onPlaying.bind(this)
    this.onLoading = this.onLoading.bind(this)
    this.onFinishedPlaying = this.onFinishedPlaying.bind(this)
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
  }

  onLoading(o) {
    //console.log(o)
  }

  onFinishedPlaying() {
    console.log("playback finished")
  }

  render() {
    return <div>
      <Button
          style={{ marginTop: 50 }}
          onClick={(e) => this.playPause()}
          raised={true}
      >playPause</Button>
      ::{this.state.status}::
      <Sound
              url={this.props.url}
              playStatus={this.state.status}
              onPlaying={this.onPlaying}
              onLoading={this.onLoading}
              onFinishedPlaying={this.onFinishedPlaying}
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
