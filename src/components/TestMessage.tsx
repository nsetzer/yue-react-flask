import * as React from 'react';
import PropTypes from 'prop-types';

import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import * as actionCreators from '../actions/message';
import './TestMessage.css';

import TextField from 'material-ui/TextField';
import Button from 'material-ui/Button';
import IconButton from 'material-ui/IconButton';
import * as UiList  from 'material-ui/List';
import Send from 'material-ui-icons/Send';
import Delete from 'material-ui-icons/Delete';

const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction

export interface TestMessageProps {
  statusText: string,
  messages: any[],
  getAllMessages: () => any,
  createMessage: (any) => any,
  deleteMessage: (any) => any
}

export interface TestMessageState {
  message_text: string,
}

class TestMessage extends React.Component<TestMessageProps,TestMessageState> {

  constructor(props) {
    super(props);
    this.state = {"message_text":""};
    this.updateMessageText = this.updateMessageText.bind(this)
    this.createMessage = this.createMessage.bind(this)
    this.props.getAllMessages();
  }

  updateMessageText(event) {
    this.setState({message_text: event.target.value});
  }

  createMessage(event) {
    if (this.state.message_text) {
      this.props.createMessage(this.state.message_text);
      this.setState({message_text: ""});
    }
  }

  changeMessage(event) {
    this.setState({message_text: event.target.value});
  }

  render() {
    return (
      <div>
        <h2 className="center-text"> Test Database Access</h2>

        {this.props.statusText}

        <List>
          <ListItem>

          <TextField
            type="text"
            fullWidth={true}
            placeholder="Enter a Message"
            onChange={(e) => this.changeMessage(e)}>
          </TextField>

          <ListItemSecondaryAction>
            <IconButton aria-label="Create"
             onClick={(e) => this.createMessage(e)}>
              <Send />
            </IconButton>
          </ListItemSecondaryAction>

          </ListItem>
        </List>

        <br/>

        <List>
        {
          //onClick={() => {this.props.deleteMessage(msg.id)}
          (this.props.messages) ? this.props.messages.map( (msg) => {
            return <ListItem
                     key={msg.id}>
                     <ListItemText primary={msg.text}/>
                     <ListItemSecondaryAction>
                      <IconButton aria-label="Delete"
                       onClick={() => {this.props.deleteMessage(msg.id)}}>
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                   </ListItem>
            }) : <div>No Messages To Display</div>
        }
        </List>

        <br/>
        <br/>
        <br/>
        </div>
    );
  }
}

function mapStateToProps(state) {
  return {
        statusText: state.message.statusText,
        messages: state.message.messages,
    };
}

function mapDispatchToProps(dispatch) {
    return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
    mapDispatchToProps
)(TestMessage);