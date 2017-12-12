

import * as React from 'react';
import PropTypes from 'prop-types';
//import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

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

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../utils/misc'

export interface QueueViewProps {
  queueStatus: string,
  songs: Array<any>,
  history: Array<any>,
  getQueue: () => any,
  setQueue: () => any,
  populateQueue: () => any,
};

export interface QueueViewState {
}

const listRightStyle = {
   textAlign: "right",
};

class QueueView extends React.Component<QueueViewProps,QueueViewState> {

  constructor(props) {
    super(props);
  }

  render() {
    return (
        <div>
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
)(QueueView);
