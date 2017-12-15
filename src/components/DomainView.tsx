
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

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

import * as actionCreators from '../actions/library';

import History from '../history';

export interface DomainViewProps {
  libraryStatus: string,
  libraryGetDomainInfo: () => any,
  domain_artists: Array<any>,
  domain_genres: Array<any>,
  domain_song_count: number
};

export interface DomainViewState {
}

class DomainView extends React.Component<DomainViewProps,DomainViewState> {

  constructor(props) {
    super(props);
    this.componentDidMount = this.componentDidMount.bind(this)
  }

  componentDidMount() {

    // TODO: this query only needs to run once, find a better
    // way to gate that behavior
    if(this.props.domain_song_count==0) {
      this.props.libraryGetDomainInfo();
    }
  }

  render() {
    return (
        <div>
        <List>
            {
              (this.props.domain_artists.length>0) ?
                this.props.domain_artists.map( (artist) => {
                  return <ListItem key={artist.name}
                                   button
                                   onClick={()=>{History.push("/main/library/"+artist.name)}}>
                            <ListItemText primary={artist.name} />
                            <ListItemSecondaryAction>
                              <IconButton onClick={() => {}}>
                                <MoreVert />
                              </IconButton>
                            </ListItemSecondaryAction>
                         </ListItem>
                }) : <div>No Artists To Display</div>
            }
         </List>
        </div>

    )
  }
}
function mapStateToProps(state) {
  return {
      libraryStatus: state.library.statusText,
      domain_artists: state.library.domain_artists,
      domain_genres: state.library.domain_genres,
      domain_song_count: state.library.domain_song_count,
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(DomainView);