
import * as React from 'react';
import PropTypes from 'prop-types';
//import { Link } from 'react-router-dom'
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

import * as actionCreators from '../actions/library';

export interface DomainArtistViewProps {
  libraryStatus: string,
  libraryGetDomainInfo: () => any,
  domain_artists: {}
  domain_genres: {}
  domain_song_count: number
};

export interface DomainArtistViewState {
}

class DomainArtistView extends React.Component<DomainArtistViewProps,DomainArtistViewState> {

  constructor(props) {
    super(props);
    this.componentDidMount = this.componentDidMount.bind(this)
  }

  componentDidMount() {
    this.props.libraryGetDomainInfo();
  }

  render() {
    return (
        <div>
        hello world
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
)(DomainArtistView);