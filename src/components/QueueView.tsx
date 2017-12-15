
import * as React from 'react';
import PropTypes from 'prop-types';
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
import MoreVert from 'material-ui-icons/MoreVert';
import Menu, { MenuItem } from 'material-ui/Menu';

import {
  fmtDuration,
  getSongAudioUrl,
  getSongArtUrl,
  getSongDisplayTitle,
} from '../utils/misc'

export interface IMenuOpts {
  open: boolean,
  anchorEl: any,
  song: any
}

export interface IQueueViewProps {
  queueStatus: string,
  songs: Array<any>,
  history: Array<any>,
  getQueue: () => any,
  setQueue: () => any,
  populateQueue: () => any,
};

export interface IQueueViewState {
  menuOpts: IMenuOpts
}

const listRightStyle = {
   textAlign: 'right',
};

class QueueView extends React.Component<IQueueViewProps,IQueueViewState> {

  constructor(props) {
    super(props);
    this.state = {menuOpts:{open:false, anchorEl:null, song: null}}

    this.onOpenMenu = this.onOpenMenu.bind(this)
    this.onMenuClose = this.onMenuClose.bind(this)
    this.onMenuPlay = this.onMenuPlay.bind(this)
    this.onMenuPlayNext = this.onMenuPlayNext.bind(this)
    this.onMenuRemove = this.onMenuRemove.bind(this)
  }

  public onOpenMenu(event, song) {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = true;
    menuOpts.anchorEl = event.currentTarget
    menuOpts.song = song
    this.setState({menuOpts: menuOpts});
  }

  public onMenuClose() {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
  }

  public onMenuPlay() {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
  }

  public onMenuPlayNext() {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
  }

  public onMenuRemove() {
    let menuOpts = this.state.menuOpts;
    menuOpts.open = false;
    this.setState({menuOpts: menuOpts});
  }

  public render() {
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
                                         onClick={(e) => {this.onOpenMenu(e,song)}}>
                              <MoreVert />
                             </IconButton>
                           </ListItemSecondaryAction>
                         </ListItem>
                }) : <div>No Songs To Display</div>
            }
        </List>
        <Menu
          id="simple-menu"
          anchorEl={this.state.menuOpts.anchorEl}
          open={this.state.menuOpts.open}
          onRequestClose={this.onMenuClose}>
          <MenuItem onClick={this.onMenuPlay}>Play</MenuItem>
          <MenuItem onClick={this.onMenuPlayNext}>Play Next</MenuItem>
          <MenuItem onClick={this.onMenuRemove}>Remove</MenuItem>
        </Menu>

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
